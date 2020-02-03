import hfst

from constraint import at_most_n_of
from symbols import *


class Generator:

    def generate(self):
        """
        Build a generator FST with the specified settings.
        :return: An HfstTransducer for generating candidates
        """
        return hfst.empty_fst()


class MorphGen(Generator):
    
    def __init__(self, in_alph, out_alph=None, syllabifier=None, ignore="", allow_ins=True, allow_del=True, max_ins=0):
        """
        Create a new Morphological Generator.
        :param in_alph: Phoneme inventory to work with
        :param out_alph: Restricted phoneme inventory in output (will take in_alph otherwise)
        :param syllabifier: Syllabifier to apply to output
        :param ignore: Characters to ignore in input
        :param allow_ins: Allow random insertions of output characters
        :param allow_del: Allow random deletions of input characters
        :param max_ins: Maximal number of insertions (0 = infinite)
        """
        self._alph = in_alph
        self._mut = in_alph if out_alph is None else out_alph
        self._syl = syllabifier
        self._ignore = ignore
        self._allow_ins = allow_ins
        self._allow_del = allow_del
        self._max_ins = max_ins
        
    def generate(self):
        alph = _build_regex(self._alph.get_alphabet())
        mut = _build_regex(self._mut.get_alphabet())
        ignore = "" if self._ignore == "" else " | " + self._ignore

        # Remove syllable boundaries in input and insert insyms
        gen = hfst.regex("[ " + syl_bound + ":0 | [ 0:" + in_sym + " " + alph + " ]" + ignore + " ]*")

        # Map input symbol to output symbol
        gen2 = hfst.regex("[ " + in_sym + " " + alph + " ] 0:[ " + out_sym + " " + mut + " ]")
        # Ignore specified characters
        if self._ignore != "":
            ignore_marks = hfst.regex(ignore[3:])
            gen2.disjunct(ignore_marks)
        # Insert characters
        if self._allow_ins:
            ins = "0:[ " + in_sym + " " + no_sym + " " + out_sym + " " + mut + " ]"
            gen2.disjunct(hfst.regex(ins))
        # Delete input characters
        if self._allow_del:
            dle = "[ " + in_sym + " " + alph + " ] 0:[ " + out_sym + " " + no_sym + " ]"
            gen2.disjunct(hfst.regex(dle))

        # Loop mutator and compose with gen
        gen2.repeat_star()
        gen.compose(gen2)

        # Restrict insertions if desired
        if self._max_ins > 0:
            restrict = hfst.regex(at_most_n_of(ins_sym, self._max_ins))
            gen.compose(restrict)

        # Insert syllable boundaries if required
        if self._syl is not None: gen.compose(self._syl.syllabify())

        # Insert word boundaries
        surround = hfst.regex("?* -> " + word_bound + " ... " + word_bound + " || .#. _ .#.")
        gen.compose(surround)

        gen.minimize()
        return gen
        
    
class Syllabifier:

    def syllabify(self):
        """
        Build a syllabifier FST with the specified settings.
        :return: An HfstTransducer for inserting syllable boundaries into candidates
        """
        return hfst.empty_fst()


class RandomSyllabifier(Syllabifier):
    
    def __init__(self):
        """ A syllabifier that inserts syllable and nucleus boundaries randomly. """
        
    def syllabify(self):
        c = in_sym + " \\" + out_sym + "+ " + out_sym + " \\" + in_sym + "+"
        syl = hfst.regex("0 (->) " + syl_bound + " | " + nucl_bound + " || _ " + c + " , " + c + " _")
        syl.minimize()
        return syl


class NuclearSyllabifier(Syllabifier):

    def __init__(self, alph, fill_onset=False, sonority_filter=False):
        """
        A syllabifier that requires syllables to contain exactly one nucleus (+syllabic phoneme).
        :param alph: The PhonemeInventory to get the nuclei and consonants from
        :param fill_onset: Punish C.V boundaries
        :param sonority_filter: Punish candidates with syllables not adhering to the sonority hierarchy
        """
        self._alph = alph
        self._fill_onset = fill_onset
        self._sonorous = sonority_filter

    def syllabify(self):
        v = "[ " + out_prefix + " " + _build_regex(self._alph.get_phonemes("+syllabic")) + " ]"
        c = "[ " + out_prefix + " " + _build_regex(self._alph.get_phonemes("-syllabic")) + " ]"

        fill_nucl = hfst.regex(v + " -> " + nucl_bound + " ... " + nucl_bound)
        syl = hfst.regex("0 -> " + syl_bound + " \/ " + nucl_bound + " " + c + "* _ " + c + "* " + nucl_bound)
        surround = hfst.regex("?* -> " + syl_bound + " ... " + syl_bound + " || .#. _ .#.")
        fill_nucl.compose(syl)
        fill_nucl.compose(surround)

        if self._fill_onset:
            no_vowstart = hfst.regex("~[ $[ \\" + v + " " + syl_bound + " " + nucl_bound + " ] ]")
            fill_nucl.compose(no_vowstart)

        if self._sonorous:
            son_scale = self._alph.get_sonority_scale()
            scale = list()
            for layer in son_scale[1:]:
                if not len(layer) == 0:
                    lregex = "[ " + out_prefix + " " + _build_regex(layer) + " ]"
                    scale.append(lregex)
            suffix = ""
            for layer in scale:
                suffix += " " + layer + "*"
            prefix = ""
            for layer in reversed(scale):
                prefix += layer + "* "

            son_filter = hfst.regex(syl_bound
                                    + " [ " + prefix + " "
                                    + nucl_bound + " " + v + " " + nucl_bound + " "
                                    + suffix + " " + syl_bound + " ]+ ")
            fill_nucl.compose(son_filter)

        fill_nucl.minimize()
        return fill_nucl


def _build_regex(lexemes, is_regex=False):
    if len(lexemes) == 0:
        regex = ""
    else:
        regex = "[ "
        for lexeme in lexemes:
            if is_regex:
                regex += lexeme + " | "
            else:
                regex += _escape_string(lexeme) + " | "
        regex = regex[:-3] + " ]"
    return regex


def _escape_string(string):
    esc = "["
    for ch in string:
        esc += "%" + ch
    return esc + "]"
