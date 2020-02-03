from enum import Enum
from collections import defaultdict


class PhoneticAlphabet(Enum):
    IPA = 0
    XSAMPA = 1


class PhonemeInventory:

    __sonority_scale = ["+syllabic",
                        ["+approximant", "-liquid"],
                        "+rhotic",
                        "+lateral",
                        "+nasal",
                        ["+continuant", "-affricate"],
                        "+affricate",
                        "-continuant"]

    def __init__(self, representation=PhoneticAlphabet.XSAMPA, phonemes=set(), diacritics=True):
        """
        Creates a phoneme inventory with convenience methods.
        :param representation: The phonetic alphabet used for representing the characters.
                               Supported alphabets are XSAMPA (default) and IPA.
        :param phonemes: The collection of phonemes that should be in the inventory. Will
                         include all phonemes listed in phon_symbols.tsv if given an empty
                         collection.
        :param diacritics: Whether or not the inventory contains phonemes composed of a base
                           symbols and a diacritic. You can set this to False if your phonemes
                           do not use diacritics to spare the constructor some extra loops.
        """
        phonemes = set(phonemes)
        self._phoneme_sets = defaultdict(set)
        self._feature_bundles = defaultdict(set)

        with open("phon_symbols.tsv", encoding="UTF-8") as sym_file:
            sym_lines = sym_file.readlines()
        with open("phon_diacritics.tsv", encoding="UTF-8") as dia_file:
            dia_lines = dia_file.readlines()
        sym_lines = [line.rstrip('\n') for line in sym_lines]
        dia_lines = [line.rstrip('\n') for line in dia_lines]

        header = sym_lines[1].split('\t')[2:]
        for (i, supergroup) in enumerate(sym_lines[0].split('\t')[2:]):
            feature = {"+"+header[i], "-"+header[i]}
            self._feature_bundles[header[i]] |= feature
            if supergroup != "":
                self._feature_bundles[supergroup] |= feature
        sym_lines = sym_lines[2:]
        dia_lines = dia_lines[2:] if diacritics else [dia_lines[2]]

        for sym_line in sym_lines:
            for dia_line in dia_lines:
                sym_vals = sym_line.split('\t')
                dia_vals = dia_line.split('\t')
                symbol = (sym_vals[0]+dia_vals[0]) if representation == PhoneticAlphabet.IPA \
                    else (sym_vals[1]+dia_vals[1])
                if len(phonemes) == 0 or symbol in phonemes:
                    self._phoneme_sets["alph"].add(symbol)
                    for (j, sym_val) in enumerate(sym_vals[2:]):
                        dia_val = dia_vals[j+2]
                        if dia_val != "0":
                            self._phoneme_sets[dia_val+header[j]].add(symbol)
                        elif sym_val != "0":
                            self._phoneme_sets[sym_val+header[j]].add(symbol)

    def get_alphabet(self):
        """ :return: All phonemes in the inventory """
        return self._phoneme_sets["alph"].copy()

    def get_phonemes(self, features):
        """
        Get phonemes with certain features.
        :param features: One or more features characterizing the phonemes to extract
        :return: The phonemes satisfying the condition
        """
        if isinstance(features, str): features = [features]
        phonemes = self.get_alphabet().copy()
        for feature_name in features:
            if feature_name in self._phoneme_sets:
                phonemes &= self._phoneme_sets[feature_name].copy()
            else:
                phonemes = set()
                print("No feature " + feature_name + " in this inventory")
        return phonemes

    def get_feature_bundles(self, features, value="", filtr=None):
        """
        Get a list of sets of phonemes, one for each distinct feature in the bundle
        specified by features.
        :param features: One or more references to a feature bundle (e.g. "manner2" or "round") or
                         a distinct feature (e.g. "+voice")
        :param value: "+" or "-" if feature bundles should only be resolved to either value.
        :param filtr: Features that all bundles returned must fulfill (e.g. "+syllabic" to only
                      return vowels).
        :return: A list of phoneme bundles corresponding to the distinct features in the
                 given feature bundle.
        """
        if isinstance(features, str): features = [features]
        feature_sets = list()
        filter_phons = self.get_alphabet() if filtr is None else self.get_phonemes(filtr)
        self.__add_feature_bundle(features, feature_sets, value, filter_phons)
        return feature_sets

    def __add_feature_bundle(self, features, feature_bundles, value, filtr):
        for feature_name in features:
            if feature_name in self._phoneme_sets:
                if feature_name.startswith(value):
                    feature_bundle = self._phoneme_sets[feature_name] & filtr
                    feature_bundles.append(feature_bundle)
            elif feature_name in self._feature_bundles:
                self.__add_feature_bundle(self._feature_bundles.get(feature_name), feature_bundles, value, filtr)
            else:
                print("No feature " + feature_name + " in this inventory, ignoring it")

    def get_sonority_scale(self, scale=__sonority_scale):
        """
        Get a list of sets of phonemes corresponding to the levels of a
        given sonority scale. Each phoneme will only be included on the
        highest applicable level (so no duplicates).
        :param scale: The sonority scale
        :return: All phonemes ordered along the sonority scale
        """
        scaled_phon = list()
        all_phon = self.get_alphabet().copy()
        for step in scale:
            level = self.get_phonemes(step).copy()
            level &= all_phon
            all_phon -= level
            scaled_phon.append(level)
        if len(all_phon) > 0:
            print("Phonemes not covered by scale:", all_phon)
        return scaled_phon


