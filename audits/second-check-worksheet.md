# Second-check worksheet (AI, independent of verify.py)

Two separate agents re-opened every cited filing line and recomputed every ratio in
Python. This sheet was a reference only. The human sign-off is in the Your mark column of each
audit, entered by me after opening each line with `sed -n '<line>p' runs/<run>/<file>` and confirming it.

## COST — runs/COST_2026-10-27_174839/

Result: 17 of 17 Correct. Errors 0, missing 0.

| Row | Second check | Line to open / arithmetic |
|---|---|---|
| 1 | Correct | 10-K.txt:673 "Total revenue 303,154 275,235 254,453" |
| 2 | Correct | 303,154 / 275,235 - 1 = 10.14% |
| 3 | Correct | 10-K.txt:677 "Operating income 11,685 10,383 9,285"; 11,685 / 303,154 = 3.85% |
| 4 | Correct | 10-K.txt:683 "NET INCOME $ 9,226 $ 8,099 $ 7,367" |
| 5 | Correct | 10-K.txt:686 "Diluted $ 20.76 $ 18.21 $ 16.56" |
| 6 | Correct | 10-K.txt:742 "TOTAL EQUITY 35,803 29,164" (no noncontrolling interest); 9,226 / 32,483.5 = 28.40% |
| 7 | Correct | 10-K.txt:727 current LTD 2,248; :731 LTD 3,914; (3,914 + 2,248) / 35,803 = 0.17x |
| 8 | Correct | 10-K.txt:794 CFO 15,817; :796 capex (6,435); FCF 9,382 |
| 9 | Correct | release-ex99-1.txt:39 "Total revenue 95,723 86,156 ..." |
| 10 | Correct | 95,723 / 86,156 - 1 = 11.10% |
| 11 | Correct | release-ex99-1.txt:52 "Diluted $ 6.75 $ 5.87 ..." |
| P/E | Correct | 992.13 / 20.76 = 47.8x |
| Peer WMT | Correct | runs/WMT_2026-10-27_175416/10-K.txt:770 revenue 713,163; :774 op income 29,825 → 4.18% |
| Peer TGT | Correct (XBRL facts only) | facts.json: 5,117 / 104,780 = 4.88%. The TGT 10-K is not saved locally |
| Peer BJ | Correct (XBRL facts only) | facts.json: 816.6 / 21,457.3 = 3.81%. The BJ 10-K is not saved locally |
| Template | Correct | report.md has headings ## 1 to ## 5 |
| Recommendation | Correct | report.md:226 "Rating: Hold"; :228 states 47.8x |

Notes:
- The 10-K gives CFO 15,817. The release gives 15,825, marked "subject to reclassification". The report uses the 10-K figure and says so.

## KO — runs/KO_2026-10-27_175126/

Result: 17 of 17 Correct. Errors 0, missing 0.

| Row | Second check | Line to open / arithmetic |
|---|---|---|
| 1 | Correct | 10-K.txt:1067 "Net Operating Revenues $ 47,941 $ 47,061 $ 45,754" |
| 2 | Correct | 47,941 / 47,061 - 1 = 1.87% |
| 3 | Correct | 10-K.txt:1072 "Operating Income 13,762 9,992 11,311"; 13,762 / 47,941 = 28.71% |
| 4 | Correct | 10-K.txt:1217 net income attributable to shareowners 13,107 |
| 5 | Correct | 10-K.txt:1083 "Diluted Net Income Per Share 1 $ 3.04 $ 2.46 $ 2.47" |
| 6 | Correct | Shareowners' equity 32,169 / 24,856 (10-K.txt:1145, :1229); 13,107 / 28,512 = 45.97% |
| 7 | Correct (definition note) | 10-K.txt:1136 LTD 42,119; :1132 current maturities 1,822; / 32,169 = 1.37x |
| 8 | Correct | 10-K.txt:1167 CFO 7,408; :1173 capex (2,112); FCF 5,296 |
| 9 | Correct | release-ex99-1.txt:210 "Net Operating Revenues $ 13,380 $ 12,455 7" |
| 10 | Correct | 13,380 / 12,455 - 1 = 7.43% |
| 11 | Correct | release-ex99-1.txt:226 "Diluted Net Income Per Share 1 $ 0.93 $ 0.86 8" |
| P/E | Correct | 91.18 / 3.04 = 30.0x |
| Peer PEP | Correct | facts.json: 11,498 / 93,925 = 12.24% |
| Peer KDP | Correct | facts.json: 3,575 / 16,603 = 21.53% |
| Peer MNST | Correct | facts.json: 2,419.4 / 8,294.3 = 29.17% |
| Template | Correct | report.md has headings ## 1 to ## 5 |
| Recommendation | Correct | report.md:281 "Rating: Hold"; :283 states 30.0x |

Notes:
- Row 7 leaves out "Loans and notes payable" of 1,551 (10-K.txt:1131, mostly commercial paper). The report defines the ratio as "long-term debt incl. current portion / equity", so the number is correct as defined. With notes payable included, the ratio is 1.41x. This is a definition choice, not an error.
- Peers in both audits are checked against XBRL facts.json only, not against the peers' own 10-K text.
