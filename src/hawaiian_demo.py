from constraint import FaithfulnessConstraint, ComplexCodaConstraint, \
    ComplexOnsetConstraint, MaximalityConstraint, DependencyConstraint, FaithfulnessConstraintBundle, \
    MarkednessConstraint
from gen import MorphGen, NuclearSyllabifier
from phonemes import PhonemeInventory
from tableau import Tableau

if __name__ == '__main__':
    # Define alphabet
    alph_en = {'A','A:','Q','{','V','e','E','@','i','i:','I','1','O','O:','u','u:','U',
               'm','n','N','p','b','t','d','k','g','t)S','d)Z','f','v','T','D','s','z','S','Z','h','l','r\\','j','w'}
    alph_hw = {'a','e','i','o','u','a:','e:','i:','o:','u:','p','k','m','n','l','w','h','?'}
    phono = PhonemeInventory(phonemes=alph_en | alph_hw)
    hw_phono = PhonemeInventory(phonemes=alph_hw)

    # Define constraints
    no_foreign = MarkednessConstraint(alph_en-alph_hw, name="*foreign")
    faith_cv = FaithfulnessConstraintBundle(phono.get_feature_bundles("consonantal"), name="ID(cons)")
    max_io = MaximalityConstraint(name="Max(IO)")
    no_complex_onset = ComplexOnsetConstraint(phono.get_phonemes(["-syllabic"]), name="NoComplexOnset")
    no_coda = ComplexCodaConstraint(phono.get_phonemes(["-syllabic"]), name="NoCoda")
    dep_io = DependencyConstraint(name="Dep(IO)")
    faith_obstruent = FaithfulnessConstraintBundle(phono.get_feature_bundles("sonorant"), name="ID(obstruent)")
    faith_liquid = FaithfulnessConstraint(phono.get_phonemes("+liquid"), name="ID(liquid)")
    faith_nasal = FaithfulnessConstraint(phono.get_phonemes("+nasal"), name="ID(nasal)")
    faith_artic = FaithfulnessConstraintBundle(phono.get_feature_bundles(["+labial", "+lingual"]), name="ID(artic)")
    faith_length = FaithfulnessConstraintBundle(phono.get_feature_bundles("long"), name="ID(length)")
    faith_backness = FaithfulnessConstraintBundle(phono.get_feature_bundles("backness"), name="ID(backness)")
    faith_height = FaithfulnessConstraintBundle(phono.get_feature_bundles("height"), name="ID(height)")
    faith_place = FaithfulnessConstraintBundle(phono.get_feature_bundles("place2", value="+"), name="ID(place)")

    # Setting up the tableau
    syl = NuclearSyllabifier(hw_phono)
    gen = MorphGen(phono, out_alph=hw_phono, syllabifier=syl)
    tab = Tableau(gen, penal_method="matching")
    constraints = [
        faith_cv,
        max_io,
        no_complex_onset,
        no_coda,
        dep_io,
        faith_obstruent,
        faith_liquid,
        faith_nasal,
        faith_artic,
        faith_length,
        faith_backness,
        faith_height,
        faith_place
    ]

    # Building the tableau
    tab.add_constraints(constraints)
    tab.build(verbosity=2)

    # Saving and loading
    tab.save("en2hw")
    tab = Tableau.load("en2hw.tableau", "en2hw.hfst")

    # Testing input
    tab.run("lEt@", "le.ka")
    tab.run("fr\\Qg", "po.lo.ka")
    tab.run("kaNg@r\\u:", "ka.na.ka.lu:")

    vow = "(a|e|i|o|u):?"
    tab.run("fr\\Qg", "po.lo.ka", n=100)
    tab.run("fr\\Qg", "p%s\.lo\.k%s" % (vow, vow), n=100, regex=True)
    tab.run("kaNg@r\\u:", "ka\.n%s\.ka\.lu:" % vow, regex=True)

    tab.trace_candidates("lEt@",
                         ["le.ka", "li.ka", "le.ke", "le.pa", "le.na", "le.ia"],
                         n=100000, show_traced_only=True, verbose=False)
    tab.trace_candidates("fr\\Qg",
                         ["plok", "po.lok", "po", "po.no.ka", "mo.lo.ka",
                          "ko.lo.ka", "po.la.ka", "po.lu.ka", "po.lo.ka"],
                         n=100000, show_traced_only=True, verbose=False)

    tab.run("tIkIt", "ki\.ki\.k%s" % vow, regex=True)
    tab.run("sIlk", "ki\.l%s\.k%s" % (vow, vow), n=100, regex=True)
