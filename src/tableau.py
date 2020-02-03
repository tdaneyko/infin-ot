import hfst
import re
import time

from constraint import penalize, pardon, Constraint
from gen import Generator
from symbols import *


class Tableau:

    _align_syms = r"\>[^\<]+\<|\,"
    _epsilon = r"@_EPSILON_SYMBOL_@"
    _out_mark_chars = r"\>[^\<]+\<|\-|\*|\,|#\.|\.#"

    def __init__(self, gen, penal_method="matching"):
        """
        :param gen: A candidate generator (either Generator or HfstTransducer object)
        :param penal_method: Use matching (default) or counting approach for removal of marked candidates
        """
        self._gen = gen.generate() if isinstance(gen, Generator) else gen
        self._penal_method = penal_method
        self._constraints = list()
        self._runnable = hfst.empty_fst()  # Final FST for simple lookup
        self._stepwise = list()  # Intermediate FSTs for candidate tracing

    def add_constraint(self, constraint):
        """
        Add a single constraint.
        :param constraint: A Constraint
        """
        self._constraints.append(constraint)

    def add_constraints(self, constraints):
        """
        Add multiple constraints.
        :param constraints: An ordered list of Constraints
        """
        self._constraints += constraints

    def save(self, file_name):
        """
        Save the tableau to file for later usage. Creates two files: <file_name>.tableau, a plain text file
        containing the constraint settings and regexes, and <file_name>.hfst, a binary HFST file containing
        the transducers (order: gen, <before_penal1, after_penal1>, <...>, final).
        :param file_name: Path and name of the save files
        """
        with open(file_name + ".tableau", "w", encoding="utf8") as tab_file:
            tab_file.write(self._penal_method + "\n")
            for constraint in self._constraints:
                tab_file.write(str(constraint) + "\n")

        fst_file = hfst.HfstOutputStream(filename=file_name + ".hfst")
        self._write_ol_fst_to(self._gen, fst_file)
        for (before, after) in self._stepwise:
            self._write_ol_fst_to(before, fst_file)
            self._write_ol_fst_to(after, fst_file)
        self._write_ol_fst_to(self._runnable, fst_file)
        fst_file.close()

    @staticmethod
    def _write_ol_fst_to(fst, outstream):
        fst.remove_optimization()
        outstream.write(fst)
        Tableau._optimize_lookup(fst)

    @staticmethod
    def _optimize_lookup(fst):
        if not fst.is_infinitely_ambiguous():
            fst.convert(hfst.ImplementationType.HFST_OL_TYPE)

    @classmethod
    def load(cls, tab_file, fst_file):
        """
        Load a Tableau object from file.
        :param tab_file: The .tableau file
        :param fst_file: The .hfst file
        :return: A Tableau object
        """
        with open(tab_file, "r", encoding="utf8") as t_file:
            lines = t_file.readlines()
        penal_method = lines[0].rstrip("\n")

        f_file = hfst.HfstInputStream(fst_file)
        gen = f_file.read()
        cls._optimize_lookup(gen)

        tab = cls(gen, penal_method=penal_method)

        stepwise = list()
        while not f_file.is_eof():
            fst_1 = f_file.read()
            cls._optimize_lookup(fst_1)
            if f_file.is_eof():
                tab._runnable = fst_1
            else:
                fst_2 = f_file.read()
                cls._optimize_lookup(fst_2)
                stepwise.append((fst_1, fst_2))
        tab._stepwise = stepwise
        f_file.close()

        for line in lines[1:]:
            fields = line.rstrip("\n").split("\t")
            name = fields[0]
            n = int(fields[1])
            regex = fields[2]
            constraint = Constraint(regex, n=n, name=name)
            tab.add_constraint(constraint)

        return tab

    def build(self, verbosity=1):
        """
        Build the tableau FST from the submitted gen and constraints.
        :param verbosity: Amount of information to be printed during building. 0 = print nothing,
                          1 = print progress in single line (default), 2+ = print time and FST size
                          for each constraint
        """
        start = time.time()

        self._gen.remove_optimization()
        self._runnable = self._gen.copy()
        self._optimize_lookup(self._gen)
        if verbosity > 1:
            print("Gen: %d states, %d arcs" % (self._runnable.number_of_states(), self._runnable.number_of_arcs()),
                  flush=True)

        n = len(self._constraints)
        for (i, constraint) in enumerate(self._constraints):
            c_start = time.time()
            if verbosity == 1:
                print("\rApplying constraints... (%d/%d)" % (i, n), end="", flush=True)
            elif verbosity > 1:
                print("Constraint %d: " % i, end="", flush=True)
            constraint.apply(self._runnable, no_penalty=True)
            self._runnable.minimize()
            before = self._runnable.copy()
            self._optimize_lookup(before)
            penalize(self._runnable, constraint.n(), no_pardon=True, method=self._penal_method)
            self._runnable.minimize()
            after = self._runnable.copy()
            self._optimize_lookup(after)
            pardon(self._runnable)
            self._runnable.minimize()
            self._stepwise.append((before, after))
            if verbosity > 1:
                c_end = time.time()
                print("%d states, %d arcs (%.2f sec.)" %
                      (self._runnable.number_of_states(), self._runnable.number_of_arcs(), c_end-c_start), flush=True)

        finish = hfst.regex(out_prefix
                            + " | " + word_bound + " " + syl_bound
                            + " | " + syl_bound + " " + word_bound
                            + " | " + nucl_bound + " -> 0")
        finish2 = hfst.regex(no_sym + " -> 0")
        finish.compose(finish2)
        self._runnable.compose(finish)
        self._runnable.minimize()
        if verbosity > 1:
            print("Final: %d states, %d arcs" % (self._runnable.number_of_states(), self._runnable.number_of_arcs()),
                  flush=True)
        self._optimize_lookup(self._runnable)

        end = time.time()
        if verbosity > 0:
            if verbosity == 1: print("\r", end="")
            print("Build complete in %.2f seconds." % (end-start), flush=True)

    def run(self, input_string, desired_winner="", regex=False, n=10):
        """
        Get the winner(s) for an input string and print it/them.
        :param input_string: The input from the source language
        :param desired_winner: The desired winner in the recipient language
        :param regex: Set to True if desired_winner is a regular expression, not a string
        :param n: Number of winners to be retrieved
        """
        if desired_winner == "": desired_winner = input_string
        winners = Tableau._weightless_lookup(self._runnable, input_string, n=n * 2)
        too_many = len(winners) > n

        if regex:
            win_re = re.compile(desired_winner+"$")
            matches = {win for win in winners if win_re.match(win)}
            if len(matches) > 0:
                winners -= matches
                winners.add(desired_winner)

        if too_many:
            print("Too many winners:")
        else:
            quot = "/" if regex else "'"
            if desired_winner in winners:
                winners.remove(desired_winner)
                print(quot + desired_winner + quot + " wins"
                      + (", but there are also other winners:" if len(winners) > 0 else "!"))
            else:
                print(quot + desired_winner + quot + " loses against:")

        for winner in list(winners)[:n]:
            print("\'" + winner + "\'")
        if too_many:
            print("etc.")

    def trace_candidates(self, input_string, traced, show_traced_only=False, verbose=False, n=10):
        """
        Trace a list of candidates across the constraints, printing information about survivors and fatalities
        after each constraint.
        :param input_string: The input from the source language
        :param traced: A list of candidates to be traced
        :param show_traced_only: If True, do not print untraced candidates (recommended for large n)
        :param verbose: If True, print candidates in raw format (i.e. with aligned input-output and all
                        boundary marks)
        :param n: The number of candidates to be retrieved at each step
        :return:
        """
        gen_inf = self._gen.is_infinitely_ambiguous()
        candidates = None if gen_inf else Tableau._reformat(
            Tableau._weightless_lookup(self._gen, input_string, n=n + 1), verbose)
        print("0")
        Tableau._print_lookup(candidates, traced, "Candidates", n, show_traced_only)

        # Apply constraints
        for (i, (before, after)) in enumerate(self._stepwise):
            # Get marked candidates
            fatal_inf = before.is_infinitely_ambiguous()
            fatalities = None if fatal_inf else Tableau._reformat(
                Tableau._weightless_lookup(before, input_string, n=n + 1), verbose)
            # Get survivors
            surviv_inf = after.is_infinitely_ambiguous()
            survivors = None if surviv_inf else Tableau._reformat(
                Tableau._weightless_lookup(after, input_string, n=n + 1), verbose)
            # Get fatalities
            fatal_unknown = fatal_inf or len(fatalities) > n
            if not fatal_unknown: fatalities -= survivors
            # Print results
            print(str(i+1))
            Tableau._print_lookup(fatalities, traced, "Fatalities", n, show_traced_only,
                                  numbers_exact=not fatal_unknown)
            Tableau._print_lookup(survivors, traced, "Survivors", n, show_traced_only)

    @staticmethod
    def _weightless_lookup(fst, input_string, n=20):
        lookup = fst.lookup(input_string, max_number=n)
        winners = set()
        for winner in lookup:
            winners.add(winner[0])
        return winners

    @staticmethod
    def _reformat(candidates, verbose):
        candidates = {re.sub(Tableau._epsilon, "", cand) for cand in candidates}
        if not verbose: candidates = {re.sub(Tableau._align_syms, "", cand) for cand in candidates}
        return candidates

    @staticmethod
    def _print_lookup(output, traced, label, n, show_traced_only, numbers_exact=True):
        if output is None:
            print(label + ": (infinite)")
        elif len(output) > n:
            print(label + ": > " + str(n))
        else:
            if numbers_exact:
                print(label + ": " + str(len(output)))
                if len(output) > 0:
                    trace_match = set()
                    trace_others = set()
                    for cand in output:
                        norm_cand = re.sub(Tableau._out_mark_chars, "", cand)
                        if norm_cand in traced: trace_match.add(cand)
                        elif len(trace_others) <= n: trace_others.add(cand)
                    print("\ttraced: " + ("(none)" if len(trace_match) == 0 else str(trace_match)))
                    if not show_traced_only:
                        print("\tuntraced: " + ("(none)" if len(trace_others) == 0 else str(trace_others)))
            else:
                print(label + ": <= " + str(n))
