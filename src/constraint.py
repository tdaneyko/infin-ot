import hfst
from enum import Enum

from symbols import *


class Scope(Enum):
    """ The scope of a constraint, i.e. the part of an input it should apply within. """
    PHRASE = 0
    WORD = 1
    SYLLABLE = 2
    ONSET = 3
    NUCLEUS = 4
    CODA = 5
    CONS_CLUSTER = 6

    def ignore(self):
        """ :return: A regex for the boundary marks to ignore given the scope of the constraint. """
        if self is Scope.ONSET or self is Scope.NUCLEUS or self is Scope.CODA: return ""
        if self is Scope.CONS_CLUSTER: return syl_bound
        ignore = "[ " + nucl_bound
        if self is Scope.PHRASE: ignore += " | " + word_bound
        if self is not Scope.SYLLABLE: ignore += " | " + syl_bound
        ignore += " ]"
        return ignore

    def left_border(self):
        """ :return: The left boundary mark of the scope. """
        border = ""
        if self is Scope.PHRASE: border = ".#."
        elif self is Scope.WORD: border = word_bound
        elif self is Scope.SYLLABLE or self is Scope.ONSET: border = syl_bound
        elif self is Scope.NUCLEUS or self is Scope.CODA or self is Scope.CONS_CLUSTER: border = nucl_bound
        return border

    def right_border(self):
        """ :return: The right boundary mark of the scope. """
        border = ""
        if self is Scope.PHRASE: border = ".#."
        elif self is Scope.WORD: border = word_bound
        elif self is Scope.SYLLABLE or self is Scope.CODA: border = syl_bound
        elif self is Scope.NUCLEUS or self is Scope.ONSET or self is Scope.CONS_CLUSTER: border = nucl_bound
        return border


class Constraint:
    """ A very basic constraint that applies a regular expression. """

    def __init__(self, regex, n=5, name=None):
        """
        :param regex: A regular expression that inserts violation marks into the input
        :param n: The penalization precision for the counting approach
        """
        self._regex = regex
        self._n = n
        self._name = str(id(self._regex)) if name is None else name

    def apply(self, candidates, no_penalty=False, no_pardon=False, method="matching"):
        """
        Apply the constraint to the current candidate set, i.e. compose the candidates with
        the constraint FST inserting the violation marks.
        :param candidates: The FST generating the current candidate set
        :param no_penalty: Do not remove losers if True
        :param no_pardon: Do not remove violation marks if True
        :param method: The penalization method to apply, matching (default) or counting
        :return: The updated candidate set FST
        """
        candidates.compose(hfst.regex(self._regex))
        if not no_penalty:
            penalize(candidates, n=self._n, no_pardon=no_pardon, method=method)
        return candidates

    def n(self):
        return self._n

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def __str__(self):
        return self._name + "\t" + str(self._n) + "\t" + self._regex


class SingleConstraint(Constraint):
    """ A constraint marking a single violation. """

    def __init__(self, violation, left="", right="", n=5, name=None):
        """
        :param violation: The regex representing the violation to be marked
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        regex = violation + " @> ... " + mark_sym
        if left != "" or right != "":
            regex += " || " + left + " _ " + right
        super().__init__(regex, n=n, name=name)


class ConstraintBundle(Constraint):
    """ A bundle of multiple constraints to be applied simultaneously. """

    def __init__(self, constraints, n=15, name=None):
        """
        :param constraints: A collection of constraints
        :param n: The penalization precision for the counting approach
        """
        regex = ""
        for constraint in constraints:
            c_re = str(constraint).split("\t")[2]
            regex += c_re + " .o. "
        regex = regex[:-5]
        super().__init__(regex, n=n, name=name)


class MarkednessConstraint(SingleConstraint):
    """ A single categorical markedness constraint. """

    def __init__(self, violation, single_symbol=False, prefix=out_prefix, ignore=None, scope=Scope.WORD,
                 left="", right="", n=5, name=None):
        """
        :param violation: The phonemes that are marked. Either a collection of phonemes (= any of these will be marked)
                          or a list of collections of phonemes (= the concatenation of these collections will be marked)
                          or a single string (= interpreted as a regex).
        :param single_symbol: May be set to True if a regex violation represents just a single phoneme to simplify
                              the constraint FST (not necessary)
        :param prefix: The regex that should directly precede the violation. DO NOT CHANGE unless you know what you
                       are doing.
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        if ignore is None: ignore = list()
        ignore.append(ignore_mark_input)
        ignore.append(scope.ignore())
        violation = _parse_violation(violation)
        if type(violation) is not str: violation = " ".join(violation)
        if not single_symbol: violation = _ignore(violation, ignore)
        violation = prefix + " " + violation
        left = _parse_context(left)
        right = _parse_context(right)
        if left != "": left = _ignore(left, ignore)
        if right != "": right = _ignore(right, ignore)
        super().__init__(violation, left=left, right=right, n=n, name=name)


class MarkednessConstraintBundle(ConstraintBundle):
    """ A bundle of simultaneously executed categorical markedness constraints. """

    def __init__(self, violations, single_symbol=False, prefix=out_prefix, ignore=None, scope=Scope.WORD,
                 left="", right="", n=15, name=None):
        """
        :param violations: A list of violations, each of which will be fed to a separate CategoricalMarkednessConstraint
                          constructor
        :param single_symbol: May be set to True if a regex violation represents just a single phoneme to simplify
                              the constraint FST (not necessary)
        :param prefix: The regex that should directly precede the violation. DO NOT CHANGE unless you know what you
                       are doing.
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        if ignore is None: ignore = list()
        ignore.append(mark_sym)
        constraints = [MarkednessConstraint(violation, single_symbol=single_symbol, prefix=prefix,
                                            ignore=ignore, scope=scope, left=left, right=right)
                       for violation in violations]
        super().__init__(constraints, n=n, name=name)


class FaithfulnessConstraint(SingleConstraint):
    """ A single faithfulness constraint. """

    def __init__(self, must_keep, ignore=None, scope=Scope.WORD, left="", right="", n=5, name=None):
        """
        :param must_keep: The phonemes that should match in input and output. Either a collection of phonemes
                          or a single string (= interpreted as a regex).
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        if ignore is None: ignore = list()
        ignore.append(ignore_mark_input)
        ignore.append(scope.ignore())
        left = _parse_context(left)
        right = _parse_context(right)
        if left != "": left = _ignore(left, ignore)
        if right != "": right = _ignore(right, ignore)
        must_keep = _parse_violation(must_keep)
        must_keep = "[ " + in_sym + " " + must_keep + " " + out_sym + " \\" + must_keep + " ]"
        super().__init__(must_keep, left=left, right=right, n=n, name=name)


class FaithfulnessConstraintBundle(ConstraintBundle):
    """ A bundle of simultaneously executed faithfulness constraints. """

    def __init__(self, must_keeps, ignore=None, scope=Scope.WORD, left="", right="", n=15, name=None):
        """
        :param must_keeps: A list of phoneme sets to match, each of which will be fed to a separate
                          FaithfulnessConstraint constructor
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        if ignore is None: ignore = list()
        ignore.append(mark_sym)
        constraints = [FaithfulnessConstraint(must_keep, ignore=ignore, scope=scope, left=left, right=right)
                       for must_keep in must_keeps]
        super().__init__(constraints, n=n, name=name)


class MaximalityConstraint(MarkednessConstraint):

    def __init__(self, maximality=any_in, scope=Scope.WORD, ignore=None, left="", right="", n=5, name=None):
        """
        :param maximality: The phonemes that should not be deleted (default = any)
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        maximality = "[ " + in_sym + " " + _parse_violation(maximality) + " " + out_sym + " " + no_sym + " ]"
        super().__init__(maximality, single_symbol=True, prefix="", scope=scope, ignore=ignore,
                         left=left, right=right, n=n, name=name)


class DependencyConstraint(MarkednessConstraint):

    def __init__(self, dependency=any_out, scope=Scope.WORD, ignore=None, left="", right="", n=5, name=None):
        """
        :param dependency: The phonemes that should not be inserted (default = any)
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param left: The left context
        :param right: The right context
        :param n: The penalization precision for the counting approach
        """
        dependency = "[ " + in_sym + " " + no_sym + " " + out_sym + " " + _parse_violation(dependency) + " ]"
        super().__init__(dependency, single_symbol=True, prefix="", scope=scope, ignore=ignore,
                         left=left, right=right, n=n, name=name)


class GradientConstraint(MarkednessConstraint):
    """ A single gradient markedness constraint. """

    def __init__(self, violation, left_oriented=True, ignore=None, scope=Scope.WORD, border=None, left="", right="",
                 max_size=0, n=5, name=None):
        """
        :param violation: The phonemes that are marked. Either a collection of phonemes (= any of these will be marked)
                          or a single string (= interpreted as a regex).
        :param left_oriented: True if the gradient starts at the left border of the scope, False if it starts from
                              the right
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param border: A regex representing the border at which to begin the gradient. If None, the default border
                       of the scope will be used.
        :param left: The left context
        :param right: The right context
        :param max_size: The maximum number of violations allowed next to the border
        :param n: The penalization precision for the counting approach
        """
        violation = _parse_violation(violation)
        violation = "[ " + out_prefix + " " + violation + " ]"
        left = _parse_context(left)
        right = _parse_context(right)
        gradient = violation + "^" + str(max_size) if max_size > 0 else ""
        if left_oriented:
            if border is None: border = scope.left_border()
            left = border + " " + left + " " + gradient + " " + violation + "*"
        else:
            if border is None: border = scope.right_border()
            right = violation + "* " + gradient + " " + right + " " + border
        super().__init__(violation, single_symbol=True, prefix="", ignore=ignore, scope=scope,
                         left=left, right=right, n=n, name=name)


class HorizontalGradientConstraint(ConstraintBundle):
    def __init__(self, violation, left_oriented=True, ignore=None, scope=Scope.WORD, border=None, left="", right="",
                 max_size=0, depth=10, n=5, name=None):
        """
        :param violation: The phonemes that are marked. Either a collection of phonemes (= any of these will be marked)
                          or a single string (= interpreted as a regex).
        :param left_oriented: True if the gradient starts at the left border of the scope, False if it starts from
                              the right
        :param ignore: A list of regexes that may occur and should be ignored within the violation
        :param scope: The scope of the constraint, i.e. in which parts of the string to match violation + contexts
        :param border: A regex representing the border at which to begin the gradient. If None, the default border
                       of the scope will be used.
        :param left: The left context
        :param right: The right context
        :param max_size: The maximum number of violations allowed next to the border
        :param depth: The depth/precision of the horizontal gradient (i.e. the maximum distance to be marked precisely)
        :param n: The penalization precision for the counting approach
        """
        constraints = list()
        for i in range(depth):
            j = max_size + i
            constraints.append(GradientConstraint(violation, left_oriented=left_oriented,
                                                  ignore=ignore, scope=scope, border=border,
                                                  left=left, right=right, max_size=j))
        super().__init__(constraints, n=n, name=name)


class ComplexOnsetConstraint(GradientConstraint):
    """ A constraint that punishes onsets of a certain complexity. """

    def __init__(self, onset, max_size=1, n=10, name=None):
        """
        :param onset: The set of phonemes that may not occur in the onset more than max_size times
        :param max_size: The maximum of occurrences that are allowed
        :param n: The penalization precision for the counting approach
        """
        super().__init__(onset, scope=Scope.ONSET, max_size=max_size, n=n, name=name)


class ComplexCodaConstraint(GradientConstraint):
    """ A constraint that punishes codas of a certain complexity. """

    def __init__(self, coda, max_size=0, n=10, name=None):
        """
        :param coda: The set of phonemes that may not occur in the coda more than max_size times
        :param max_size: The maximum of occurrences that are allowed
        :param n: The penalization precision for the counting approach
        """
        super().__init__(coda, scope=Scope.CODA, left_oriented=False, max_size=max_size, n=n, name=name)


class AssimilationConstraint(ConstraintBundle):
    """ A constraint that punishes dissimilar consonant clusters. """

    def __init__(self, feature_bundle, n=10, name=None):
        """
        :param feature_bundle: The bundle of features in which the consonants should be similar
        :param n: The penalization precision for the counting approach
        """
        constraints = list()
        for feat in feature_bundle:
            left = feat
            viol = "\\[ " + _parse_violation(feat) + " ]"
            constraints.append(MarkednessConstraint(viol, scope=Scope.CONS_CLUSTER, left=left))
        super().__init__(constraints, n=n, name=name)


def penalize(candidates, n=10, no_pardon=False, method="matching"):
    """
    Remove losing candidates.
    :param candidates: Current candidate set
    :param n: The penalization precision for the counting approach
    :param no_pardon: Do not remove violation marks if True
    :param method: Use matching (default) or counting approach
    :return: Updated candidate set FST
    """
    if method == "counting":
        for i in reversed(range(n+1)):
            penalty_i = hfst.regex(only_n_of(mark_sym, i))
            candidates.lenient_composition(penalty_i)
    else:
        # Remove modifications of gen, keep input characters and violation marks
        strip = hfst.regex("[ [ " + in_sym + ":0 [ " + no_sym + ":0 .P. ? ] ]"
                           + " | [ " + out_sym + " ? ]:0 | " + bound_syms + ":0 | " + mark_sym + " ]*")
        # Insert at least one violation mark into the string
        insert_marks = hfst.regex("[ ?* 0:" + mark_sym + "+ ?* ]+")
        # Randomly insert new output characters
        mutate_output = hfst.regex("[ ? | 0:? ]*")
        # Randomly scatter violation marks throughout the string
        permute1 = hfst.regex(
            "[ ?* " + mark_sym + ":0 ?* 0:" + mark_sym + " ?* ]*")
        permute2 = hfst.regex(
            "[ ?* 0:" + mark_sym + " ?* " + mark_sym + ":0 ?* ]*")
        # Compose everything
        worse = candidates.copy()
        worse.compose(strip)
        worse.compose(insert_marks)
        worse.compose(permute1)
        worse.compose(permute2)
        worse.compose(mutate_output)
        # Subtract worse candidates from actual candidates
        candidates.subtract(worse)
        candidates.minimize()

    if not no_pardon: pardon(candidates)
    return candidates


def pardon(constraint):
    """ Remove violation marks from surviving candidates. """
    constraint.compose(hfst.regex(mark_sym + " -> 0"))


def _parse_violation(violation):
    if type(violation) is str:
        regex = violation
    elif all(isinstance(x, str) for x in violation):
        regex = "[ " if len(violation) > 1 else ""
        for viol in violation:
            regex += _escape_string(viol) + " | "
        regex = regex[:-3]
        if len(violation) > 1: regex += " ]"
    else:
        regex = list()
        for syms in violation:
            regex.append(_parse_violation(syms))
    return regex


def _parse_context(context):
    if type(context) is str:
        return context
    context = _parse_violation(context)
    if type(context) is str:
        context = [context]
    context = [con if con in symbols_esc else "[ " + out_prefix + " " + con + " ]"
               for con in context]
    context = " ".join(context)
    return context


def _escape_string(string):
    esc = "["
    for ch in string:
        esc += "%" + ch
    return esc + "]"


def _ignore(regex, ignore):
    ign_regex = "[ " + regex + " / [ "
    for ign in ignore:
        if ign != "":
            ign_regex += ign + " | "
    return ign_regex[:-3] + " ] ]"


def at_most_n_of(regex, n):
    if n == 0:
        return "[ [ \\" + regex + " ]* ]"
    else:
        return "[ [ \\" + regex + " ]* [ " + regex + " / \\" + regex + " ]^<" + str(n+1) + " [ \\" + regex + " ]* ]"


def only_n_of(regex, n):
    return "~[ [" + regex + "]^>" + str(n) + " / ? ]"
