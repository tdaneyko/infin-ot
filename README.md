# infinOT

infinOT can execute Optimality Theory tableaux on an infinite candidate
set with the help of finite state technology. Details on the implementation
and usage can be found in the accompanying presentation and term paper
(under _doc_).

This is the semester project I did for the course "Loanword Phonology"
taught by Armin Buch and Marisa Köllner at the University of Tübingen
in the summer semester 2017.

## Abstract

Manual construction of Optimality Theory (OT) tableaux, as is still
the default procedure in contemporary linguistics, has the deﬁcit
of not covering the complete, i.e. inﬁnite, set of candidates. Even
though proposals of how to handle the inﬁnite set computationally
by using ﬁnite state transducers (FSTs) have been around for almost
20 years, current OT software provides no means of checking against
inﬁnitely many candidates. I present a new OT implementation
based on ﬁnite state technology which is able to derive a winner for
any input from an inﬁnite candidate set, while being accessible and
easy to use.

## Introduction (excerpt)

Ever since its introduction in 1993, Optimality Theory (OT; Prince and
Smolensky 2008) has been a popular framework in phonology, being able to
successfully explain a range of phonological phenomena. However, most of
the work associated with OT, especially the generation of output candidates,
is usually done by hand and rarely automated. This leads to many possible
candidates being missed: The real set of candidates is in fact inﬁnite, and while
the majority of these possible candidates is completely unrelated to the input or
even unpronounceable, we cannot speak of a thorough analysis if we are not sure
that all of the inﬁnite bad candidates have been dealt with by our constraints.
Even worse, concentrating on a handful of “human-generated” examples, it is
easy to overlook a likely candidate that outperforms the desired winner under
the current order of constraints.

To avoid such a faulty analysis due to missed candidates, Karttunen (1998)
suggests to use ﬁnite state transducers (FSTs) to generate an inﬁnite candidate
set and reduce it to a single winning candidate. An FST is able to encode
mappings between an inﬁnite amount of strings and multiple transducers can
be combined into a single one which simply yields the correct output for an
arbitrary input. Karttunen’s approach has later been improved by Gerdemann
and Noord (2000); however, there is no comprehensive implementation of their
algorithms yet.

In this paper, I introduce my ﬁnite state based Python implementation of an
OT tableau that is able to generate an inﬁnite and completely unrestricted
candidate set, mark violations of constraints and ﬁlter out losing candidates.
The ﬁnal FST is small and fast, and can produce the winner(s) for any input.
Intermediate FSTs additionally provide the possibility to view violation marks
assigned by any (ﬁnite) constraint and watch selected candidates win and lose
across the tableau. Straightforward and simple methods and classes enable easy
usage, and many options as well as the possibility to deﬁne custom generators
and constraints provide the means for building complex tableaux.
