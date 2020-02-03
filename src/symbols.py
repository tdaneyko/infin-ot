"""
Helper file defining regexes for special symbols so that they can be
centrally modified.
"""

in_sym = "[%>]"
out_sym = "[%<]"
no_sym = "[%-]"
ins_sym = "[%>%-%<]"

mark_sym = "[%*]"

word_bound = "[%#]"
syl_bound = "[%.]"
nucl_bound = "[%,]"
bound_syms = "[ " + word_bound + " | " + syl_bound + " | " + nucl_bound + " ]"

any_in = "[ \\" + out_sym + " ]+"
any_out = "[ \\[ " + in_sym + " | " + bound_syms + " ] ]+"

out_prefix = "[ " + in_sym + " " + any_in + " " + out_sym + " ]"
ignore_input = "[ " + out_prefix + " | " + no_sym + " ]"
ignore_mark_input = "[ " + out_prefix + " | " + no_sym + " | " + mark_sym + " ]"
deletion = "[ " + in_sym + " " + any_in + " " + out_sym + " " + no_sym + " ]"

symbols = [">", "<", "*", ",", ".", "#"]
symbols_esc = [in_sym, out_sym, mark_sym, nucl_bound, syl_bound, word_bound]
