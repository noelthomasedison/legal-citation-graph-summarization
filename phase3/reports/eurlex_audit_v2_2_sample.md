# EUR-Lex v2_2 graph precision audit sample

Frozen graph: `data/eurlex_edges_v2_2.jsonl` sha256 `f4b9f0ad7203d986…`

Seed 389. Population: 87,074 within-document and 10,259 cross-document edges.
Sample: 50 within + 50 cross.
Segmentation: `region-v2`. Seeds 41, 97, 173, 251 and 347
are development/repair sets; this is a fresh held-out sample.

For every row, judge whether the source passage genuinely refers to
the displayed target passage. Put `TRUE`, `FALSE`, or `UNSURE` in
the matching `label` field of `data/eurlex_audit_v2_2_sample.jsonl`.
Do not infer correctness merely because the article numbers match.

## 000 [WITHIN] `and 7 to 11`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32012R0648` / `88.1.b`
- Target act/path: `32012R0648` / `10`
- Source context: ...(b) penalties imposed for breaches of Articles 4, 5 and 7 to 11; ...
- Target text: Article 10 Non-financial counterparties 1.   Where a non-financial counterparty takes positions in OTC derivative contracts and those positions exceed the clearing threshold as specified under paragraph 3, that non-financial counterparty shall: (a) immediately notify ESMA and the competent authority referred to in paragraph 5 thereof; (b) become subject to the clearing obligation for future contracts in accordance with Article 4 if the rolling average position over 30 working days exceeds the threshold; and (c) clear all relevant future contracts within four months of becoming subject to the c

## 001 [WITHIN] `paragraph 1`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `32019R1239` / `17.3`
- Target act/path: `32019R1239` / `17.1`
- Source context: ...3.   The Commission shall adopt implementing acts laying down the technical specifications, standards and procedures for the setting up of the database referred to in paragraph 1. Those implementing acts shall be adopted in accordance with the advisory procedure referred to in Article 24(2). CHAPTER V COORDINATION OF THE EMSWe ACTIVITIES ...
- Target text: 1.   The Commission shall make available a common ship sanitation database that is able to receive and store data related to the Maritime Declarations of Health under Article 37 of the International Health Regulations 2005 (IHR). Personal data relating to ill persons on board ships shall not be stored on that database. The competent health authorities of the Member States shall have access to the database for the purpose of receiving and exchanging data.

## 002 [WITHIN] `Article 119`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32009R1224` / `65.2`
- Target act/path: `32009R1224` / `119`
- Source context: ...he market but used only for private consumption shall be exempted from the provisions laid down in Articles 62, 63 and 64. Any amendment to this threshold shall be adopted in accordance with the procedure referred to in Article 119. ...
- Target text: Article 119 Committee procedure 1.   The Commission shall be assisted by the Committee set up under Article 30 of Regulation (EC) No 2371/2002. 2.   Where reference is made to this Article, Articles 4 and 7 of Decision 1999/468/EC shall apply. The period laid down in Article 4(3) of Decision 1999/468/EC shall be set at one month. TITLE XIV AMENDMENTS AND REPEALS

## 003 [WITHIN] `paragraph 2`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `32021R1147` / `7.1`
- Target act/path: `32021R1147` / `7.2`
- Source context: ...1.   The Fund shall be open to third countries that fulfil the criteria listed in paragraph 2, in accordance with the conditions laid down in a specific agreement covering the participation of the third country in the Fund. ...
- Target text: 2.   In order for a third country to be eligible to be associated to the Fund as referred to in paragraph 1, it shall have concluded with the Union an agreement on the criteria and mechanisms for establishing the State responsible for examining a request for asylum lodged in a Member State or lodged in that third country.

## 004 [WITHIN] `Articles 230 to 233`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32009L0138` / `234`
- Target act/path: `32009L0138` / `233`
- Source context: ...Article 234 Implementing measures The Commission shall adopt implementing measures specifying the technical principles and methods set out in Articles 220 to 229 and the application of Articles 230 to 233 to ensure uniform application within the Community. Those measures, designed to amend non-essential elements of this Directive by supplementing it, shall be adopted in accordance with the regulatory procedure with scrut...
- Target text: Article 233 Method 2 (Alternative method): Deduction and aggregation method 1.   The group solvency of the participating insurance or reinsurance undertaking shall be the difference between the following: (a) the aggregated group eligible own funds, as provided for in paragraph 2; (b) the value in the participating insurance or reinsurance undertaking of the related insurance or reinsurance undertakings and the aggregated group Solvency Capital Requirement, as provided for in paragraph 3. 2.   The aggregated group eligible own funds are the sum of the following: (a) the own funds eligible for

## 005 [WITHIN] `, 5`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32016R1103` / `10`
- Target act/path: `32016R1103` / `5`
- Source context: ...Article 10 Subsidiary jurisdiction Where no court of a Member State has jurisdiction pursuant to Article 4, 5, 6, 7 or 8, or when all the courts pursuant to Article 9 have declined jurisdiction and no court has jurisdiction pursuant to Article 9(2), the courts of a Member State shall have jurisdiction in so far as immoveable pr...
- Target text: Article 5 Jurisdiction in cases of divorce, legal separation or marriage annulment 1.   Without prejudice to paragraph 2, where a court of a Member State is seised to rule on an application for divorce, legal separation or marriage annulment pursuant to Regulation (EC) No 2201/2003, the courts of that State shall have jurisdiction to rule on matters of the matrimonial property regime arising in connection with that application. 2.   Jurisdiction in matters of matrimonial property regimes under paragraph 1 shall be subject to the spouses' agreement where the court that is seised to rule on the

## 006 [WITHIN] `Article 183`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32017R1001` / `184.8`
- Target act/path: `32017R1001` / `183`
- Source context: ...vided for under Article 3(1) of the Madrid Protocol as soon as the international application meets the requirements laid down in this Article, the implementing act adopted pursuant to paragraph 9 of this Article, and in Article 183 of this Regulation. ...
- Target text: Article 183 Filing of an international application 1.   International applications pursuant to Article 3 of the Madrid Protocol based on an application for an EU trade mark or on an EU trade mark shall be filed at the Office. 2.   Where an international application is filed before the mark on which the international registration is to be based has been registered as an EU trade mark, the applicant for the international registration shall indicate whether the international registration is to be based on an EU trade mark application or registration. Where the international registration is to be

## 007 [WITHIN] `(4) OF ARTICLE 311(1)`
- Resolution: `exact`; keyword: `ARTICLE`
- Source act/path: `32006L0112` / `0`
- Target act/path: `32006L0112` / `311.1.4`
- Source context: ...T (4) OF ARTICLE 295(1) ANNEX VIII — INDICATIVE LIST OF THE AGRICULTURAL SERVICES REFERRED TO IN POINT (5) OF ARTICLE 295(1) ANNEX IX — WORKS OF ART, COLLECTORS' ITEMS AND ANTIQUES, AS REFERRED TO IN POINTS (2), (3) AND (4) OF ARTICLE 311(1) Part A — Works of art Part B — Collectors' items Part C — Antiques ANNEX X — LIST OF TRANSACTIONS COVERED BY THE DEROGATIONS REFERRED TO IN ARTICLES 370 AND 371 AND ARTICLES 380 TO 390 Part A — Transactions which Member...
- Target text: (4) ‘antiques’ means the objects listed in Annex IX, Part C;

## 008 [WITHIN] `Article 5`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R0523` / `0`
- Target act/path: `32021R0523` / `5`
- Source context: ...arliament and the Council during the annual budgetary procedure. (39) EUR 2 672 292 573 in current prices of the EU guarantee should be provisioned by resources from the additional allocation provided in accordance with Article 5 of and Annex II to Council Regulation (EU, Euratom) 2020/2093 (12) corresponding to an amount of EUR 1 000 000 000 in 2018 prices. An amount of EUR 63 800 000 in current prices of the total allocation to the InvestEU Ad...
- Target text: Article 5 Third countries associated to the InvestEU Fund The EU compartment of the InvestEU Fund referred to in point (a) of Article 9(1) of this Regulation and each of the policy windows referred to in Article 8(1) of this Regulation may receive contributions from the following third countries for the purpose of participation in certain financial products pursuant to Article 218(2) of the Financial Regulation: (a) members of the European Free Trade Association (EFTA) which are members of the EEA, in accordance with the conditions laid down in the Agreement on the European Economic Area; (b)

## 009 [WITHIN] `Article 19(11)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0596` / `38.c`
- Target act/path: `32014R0596` / `19.11`
- Source context: ...(c) the appropriateness of the conditions under which the prohibition on trading is mandated in accordance with Article 19(11) with a view to identifying whether there are any further circumstances under which the prohibition should apply; ...
- Target text: 11.   Without prejudice to Articles 14 and 15, a person discharging managerial responsibilities within an issuer shall not conduct any transactions on its own account or for the account of a third party, directly or indirectly, relating to the shares or debt instruments of the issuer or to derivatives or other financial instruments linked to them during a closed period of 30 calendar days before the announcement of an interim financial report or a year-end report which the issuer is obliged to make public according to: (a) the rules of the trading venue where the issuer’s shares are admitted t

## 010 [WITHIN] `Article 24`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R0694` / `18.4`
- Target act/path: `32021R0694` / `24`
- Source context: ...4.   The work programme referred to in Article 24 may provide that participation is limited to beneficiaries established only in Member States, or to beneficiaries established in Member States and specific associated countries or other third countries, where there are ...
- Target text: Article 24 Work programmes 1.   The Programme shall be implemented by means of work programmes as referred to in Article 110 of the Financial Regulation. 2.   Work programmes shall in principle be adopted as multiannual programmes, typically every two years, and cover the general objectives of the Programme as well as one or more specific objectives. If justified by specific implementation needs, they may also be adopted as annual programmes. 3.   Work programmes shall be consistent with the specific objectives of the Programme, as set out in Articles 4 to 8, while also taking into account the

## 011 [WITHIN] `(1) of Article 2`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32016L0943` / `11.3.b`
- Target act/path: `32016L0943` / `2.1`
- Source context: ...(b) the information in question no longer meets the requirements of point (1) of Article 2, for reasons that cannot be attributed to the respondent. ...
- Target text: (1) ‘trade secret’ means information which meets all of the following requirements: (a) it is secret in the sense that it is not, as a body or in the precise configuration and assembly of its components, generally known among or readily accessible to persons within the circles that normally deal with the kind of information in question; (b) it has commercial value because it is secret; (c) it has been subject to reasonable steps under the circumstances, by the person lawfully in control of the information, to keep it secret;

## 012 [WITHIN] `Articles 66 to 72`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32017R1001` / `193.6`
- Target act/path: `32017R1001` / `69`
- Source context: ...nd services for which the international registration is registered. The refusal of protection shall take the place of a refusal of an EU trade mark application. The decision shall be subject to appeal in accordance with Articles 66 to 72. ...
- Target text: Article 69 Revision of decisions in ex parte cases 1.   If the party which has lodged the appeal is the sole party to the procedure, and if the department whose decision is contested considers the appeal to be admissible and well founded, the department shall rectify its decision. 2.   If the decision is not rectified within one month of receipt of the statement of grounds, the appeal shall be remitted to the Board of Appeal without delay, and without comment as to its merit.

## 013 [WITHIN] `Article 87`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014L0024` / `22.7`
- Target act/path: `32014L0024` / `87`
- Source context: ...7.   The Commission shall be empowered to adopt delegated acts in accordance with Article 87 to amend the technical details and characteristics set out in Annex IV to take account of technical developments. The Commission shall be empowered to adopt delegated acts in accordance with Article 87 to amend the list...
- Target text: Article 87: Exercise of the delegation of powers

## 014 [WITHIN] `paragraph 1 (e)`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `31987D0600` / `3.3`
- Target act/path: `31987D0600` / `3.1.e`
- Source context: ...3.   The Member State referred to in Article 1 shall, in accordance with Article 36 of the Treaty, continue to inform the Commission at appropriate intervals of the levels of radioactivity as laid down in paragraph 1 (e) and (f). ...
- Target text: (e) the results of environmental monitoring;

## 015 [WITHIN] `(d) of Article 163`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `22016A0204(01)` / `170.3`
- Target act/path: `22016A0204(01)` / `163.d`
- Source context: ...n concerning exemptions, non-conforming measures, immunities and any other measures, including more favourable treatment, applicable in the territory of the requested Party to any enterprise referred to in points (a) to (d) of Article 163. ...
- Target text: (d) a ‘monopoly’ means an entity involved in a commercial activity, including a consortium, that in a relevant market in the territory of a Party is designated at central or sub-central level as the sole supplier or purchaser of a good or service, but does not include an entity that has been granted an exclusive intellectual property right solely by reason of such grant;

## 016 [WITHIN] `Article 116(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R1306` / `110.4`
- Target act/path: `32013R1306` / `116.3`
- Source context: ...void any undue administrative burden, as well as rules on the data needs and synergies between potential data sources. Those implementing acts shall be adopted in accordance with the examination procedure referred to in Article 116(3). ...
- Target text: 3.   Where reference is made to this paragraph, Article 5 of Regulation (EU) No 182/2011 shall apply. In the case of acts referred to in Article 8, where the committee delivers no opinion, the Commission shall not adopt the draft implementing act and the third subparagraph of Article 5(4) of Regulation (EU) No 182/2011 shall apply.

## 017 [WITHIN] `Article 29`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32011R0492` / `12.2`
- Target act/path: `32011R0492` / `29`
- Source context: ...2.   The Commission, taking the utmost account of the opinion of the Technical Committee referred to in Article 29 (‘the Technical Committee’), shall determine the manner in which the information referred to in paragraph 1 of this Article is to be drawn up. ...
- Target text: Article 29 The Technical Committee shall be responsible for assisting the Commission in the preparation, promotion and follow-up of all technical work and measures for giving effect to this Regulation and any supplementary measures.

## 018 [WITHIN] `Article 5`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019L0770` / `13.1`
- Target act/path: `32019L0770` / `5`
- Source context: ...1.   Where the trader has failed to supply the digital content or digital service in accordance with Article 5, the consumer shall call upon the trader to supply the digital content or digital service. If the trader then fails to supply the digital content or digital service without undue delay, or within an additional period of...
- Target text: Article 5 Supply of the digital content or digital service 1.   The trader shall supply the digital content or digital service to the consumer. Unless the parties have agreed otherwise, the trader shall supply the digital content or digital service without undue delay after the conclusion of the contract. 2.   The trader shall have complied with the obligation to supply when: (a) the digital content or any means suitable for accessing or downloading the digital content is made available or accessible to the consumer, or to a physical or virtual facility chosen by the consumer for that purpose;

## 019 [WITHIN] `Article 75`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019R1122` / `76`
- Target act/path: `32019R1122` / `75`
- Source context: ...gement If a new version or release of the Union Registry software is required, the central administrator shall ensure that the testing procedures set out in the data exchange and technical specifications provided for in Article 75 are completed before a communication link is established and activated between the new version or release of that software and the EUTL. CHAPTER 2 Records, reports, confidentiality and fees ...
- Target text: Article 75 Data exchange and technical specifications 1.   The Commission shall make available to national administrators data exchange and technical specifications laying down operational requirements for the Union Registry including the identification codes, automated checks, response codes and data logging requirements, as well as the testing procedures and security requirements. 2.   The data exchange and technical specifications shall be drawn up in consultation with the Member States. 3.   Standards developed in accordance with agreements under Article 25 of Directive 2003/87/EC shall be

## 020 [WITHIN] `point 2(b) of Article 2`
- Resolution: `exact+nested-point`; keyword: `Article`
- Source act/path: `32004L0038` / `17.2`
- Target act/path: `32004L0038` / `2.2.b`
- Source context: ...down in point (a) of paragraph 1 and the condition as to length of residence laid down in point (b) of paragraph 1 shall not apply if the worker's or the self-employed person's spouse or partner as referred to in point 2(b) of Article 2 is a national of the host Member State or has lost the nationality of that Member State by marriage to that worker or self-employed person. ...
- Target text: (b) the partner with whom the Union citizen has contracted a registered partnership, on the basis of the legislation of a Member State, if the legislation of the host Member State treats registered partnerships as equivalent to marriage and in accordance with the conditions laid down in the relevant legislation of the host Member State;

## 021 [WITHIN] `paragraph 5`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `32014R0806` / `19.11`
- Target act/path: `32014R0806` / `19.5`
- Source context: ...resolution authorities have the powers necessary to ensure compliance with any conditions laid down in a Commission decision pursuant to paragraph 3 and to recover misused amounts pursuant to a Commission decision under paragraph 5. ...
- Target text: 5.   If, on the basis of the investigations carried out by the Commission, and after giving notice to the parties concerned to submit their comments, the Commission considers that the decision under paragraph 3 has not been complied with, it shall issue a decision to the national resolution authority in the participating Member State concerned requiring that authority to recover the misused amounts within a period to be determined by the Commission. The Fund aid to be recovered pursuant to a recovery decision shall include interest at an appropriate rate fixed by the Commission and shall be pa

## 022 [WITHIN] `Article 10(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0473` / `11.1`
- Target act/path: `32013R0473` / `10.3`
- Source context: ...nder Article 126(7) TFEU or a Council decision to give notice under Article 126(9) TFEU, is at risk, the Commission shall base its assessment, inter alia, on the reports submitted by the Member States in accordance with Article 10(3) of this Regulation. ...
- Target text: 3.   The Member State shall report regularly to the Commission and to the Economic and Financial Committee, for the general government and its subsectors, the in-year budgetary execution, the budgetary impact of discretionary measures taken on both the expenditure and the revenue side, targets for the government expenditure and revenues, and information on the measures adopted and the nature of those envisaged to achieve the targets. The report shall be made public. The Commission shall be empowered to adopt delegated acts in accordance with Article 14 specifying the content of the regular rep

## 023 [WITHIN] `Article 35(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32018R1971` / `23.5`
- Target act/path: `32018R1971` / `35.3`
- Source context: ...e implementation of BEREC’s strategy for relations with competent Union bodies, offices, agencies and advisory groups, with competent authorities of third countries and with international organisations as referred to in Article 35(3), the actions linked to that strategy and the specification of associated resources. ...
- Target text: 3.   As part of the annual work programme referred to in Article 21, the Board of Regulators shall adopt BEREC’s strategy for relations with competent Union bodies, offices, agencies and advisory groups, with competent authorities of third countries and with international organisations concerning matters for which BEREC is competent. The Commission, BEREC and the BEREC Office shall conclude an appropriate working arrangement for the purpose of ensuring that BEREC and the BEREC Office operate within their mandate and the existing institutional framework.

## 024 [WITHIN] `Article 18`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0806` / `88.5`
- Target act/path: `32014R0806` / `18`
- Source context: ...ment of the effects of any disclosure of the contents and details of resolution plans as referred to in Articles 8 and 9, the result of any assessment carried out under Article 10 or the resolution scheme referred to in Article 18. ...
- Target text: Article 18 Resolution procedure 1.   The Board shall adopt a resolution scheme pursuant to paragraph 6 in relation to entities and groups referred to in Article 7(2), and to the entities and groups referred to in Article 7(4)(b) and (5) where the conditions for the application of those paragraphs are met, only when it assesses, in its executive session, on receiving a communication pursuant to the fourth subparagraph, or on its own initiative, that the following conditions are met: (a) the entity is failing or is likely to fail; (b) having regard to timing and other relevant circumstances, the

## 025 [WITHIN] `, 173`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `22021A0430(01)` / `179.1`
- Target act/path: `22021A0430(01)` / `173`
- Source context: ...1.   Each Party shall ensure that suppliers that acquire information from another supplier in the process of negotiating arrangements pursuant to Articles 169, 170, 173 and 174 use that information solely for the purpose for which it was supplied and respect at all times the confidentiality of information transmitted or stored. ...
- Target text: Article 173 Interconnection with major suppliers 1.   Each Party shall ensure that major suppliers of public telecommunications networks or public telecommunications services provide interconnection at any technically feasible point in the network. Such interconnection shall be provided: (a) under non-discriminatory terms and conditions (including as regards rates, technical standards, specifications, quality and maintenance) and of a quality no less favourable than that provided for the own like services of such major supplier, or for like services of its subsidiaries or other affiliates; (b)

## 026 [WITHIN] `Article 51`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32010R1093` / `76.2`
- Target act/path: `32010R1093` / `51`
- Source context: ...Authority until the Authority has appointed an Executive Director. For that purpose, until such time as the Executive Director takes up his duties following his appointment by the Board of Supervisors in accordance with Article 51, the Commission may assign one official on an interim basis in order to fulfil the functions of the Executive Director. That period shall be limited to the time necessary for the appointment of an Executive Director of ...
- Target text: Article 51 Appointment 1.   The Authority shall be managed by an Executive Director, who shall be a full-time independent professional. 2.   The Executive Director shall be appointed by the Board of Supervisors, after confirmation by the European Parliament, on the basis of merit, skills, knowledge of financial institutions and markets, and experience relevant to financial supervision and regulation and managerial experience, following an open selection procedure. 3.   The Executive Director’s term of office shall be 5 years and may be extended once. 4.   In the course of the 9 months precedin

## 027 [WITHIN] `, 10(9)`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32021R0023` / `87`
- Target act/path: `32021R0023` / `10.9`
- Source context: ...Article 87(2) which shall apply from 11 February 2021; Articles 9(1), 9(2), 9(3), 9(4), 9(6), 9(7), 9(9), 9(10), 9(12), 9(13), 9(16), 9(17), 9(18), 9(19), 10(1), 10(2), 10(3), 10(8), 10(9), 10(10), 10(11), 10(12) and 11 which shall apply from 12 February 2022; Articles 9(14) and 20 which shall apply from 12 February 2023. This Regulation shall be binding in its entirety and directly applicable in all Memb...
- Target text: 9.   Where the competent authority, after consulting the resolution authority and in coordination with the supervisory college in accordance with the procedure set out in Article 11, considers that the deficiencies and impediments have not been adequately addressed by the revised plan, or where the CCP has not submitted a revised plan, it shall require the CCP to make specific changes to the plan within a reasonable period, as defined by the competent authority.

## 028 [WITHIN] `Article 25(2)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32010R1031` / `33`
- Target act/path: `32010R1031` / `25.2`
- Source context: ...Article 33 Review of this Regulation Upon delivery of the annual consolidated report drawn up by the auction monitor pursuant to Article 25(2) which shall be delivered no later than 31 December 2014, the Commission shall review the arrangements provided for in this Regulation including the operation of all auction processes. The review shall analyse the experi...
- Target text: 2.   The auction monitor shall provide to the Member States and the Commission an annual consolidated report which shall comprise: (a) the matters referred to in paragraph 1 both in relation to each individual auction and in aggregate for each auction platform; (b) any failure to comply with the contract appointing an auction platform; (c) any evidence of anti-competitive behaviour or market abuse; (d) the impact of the auctions on the market position of the auction platforms on the secondary market, if any; (e) the relationship between the auction processes covered in the consolidated report

## 029 [WITHIN] `paragraphs 1 to 13`
- Resolution: `relative`; keyword: `paragraphs`
- Source act/path: `32017R0746` / `50`
- Target act/path: `32017R0746` / `74.7`
- Source context: ...Article 50(1), — Articles 66 to 73, — paragraphs 1 to 13 of Article 74, — Articles 75 to 77, — ...
- Target text: 7.   The Commission may, by means of implementing acts, further specify the procedures and timescales for coordinated assessments to be taken into account by Member States concerned when deciding on the sponsor's application. Such implementing acts may also set out the procedures and timescales for coordinated assessment in the case of substantial modifications pursuant to paragraph 12 of this Article and in the case of reporting of adverse events pursuant to Article 76(4) and in the case of performance studies involving companion diagnostics, where the medicinal products are under a concurren

## 030 [WITHIN] `and 21(1)`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32010L0024` / `26`
- Target act/path: `32010L0024` / `21.1`
- Source context: ...ll adopt, in accordance with the procedure referred to in Article 25(2), detailed rules for implementing Article 4(2), (3) and (4), Article 5(1), Articles 8, 10, 12(1), Article 13(2), (3), (4) and (5), Articles 15, 16(1) and 21(1). Those rules shall relate to at least the following: (a) the practical arrangements with regard to the organisation of the contacts between the central liaison offices, the other liaison offices and the liaison departm...
- Target text: 1.   Requests pursuant to Article 5(1) for information, requests pursuant to Article 8(1) for notification, requests pursuant to Article 10(1) for recovery or requests pursuant to Article 16(1) for precautionary measures shall be sent by electronic means, using a standard form, unless this is impracticable for technical reasons. As far as possible, these forms shall also be used for any further communication with regard to the request. The uniform instrument permitting enforcement in the requested Member State, the document permitting precautionary measures in the applicant Member State and th

## 031 [WITHIN] `paragraph 1`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `31994L0033` / `7.2.e`
- Target act/path: `31994L0033` / `7.1`
- Source context: ...(e) work in which there is a risk to health from extreme cold or heat, or from noise or vibration. Work which is likely to entail specific risks for young people within the meaning of paragraph 1 includes: — work involving harmful exposure to the physical, biological and chemical agents referred to in point I of the Annex, and — processes and work referred to in point II of the Annex. ...
- Target text: 1.   Member States shall ensure that young people are protected from any specific risks to their safety, health and development which are a consequence of their lack of experience, of absence of awareness of existing or potential risks or of the fact that young people have not yet fully matured.

## 032 [WITHIN] `Article 71`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0167` / `49.3`
- Target act/path: `32013R0167` / `71`
- Source context: ...3.   Where the Union has voted in favour of a UNECE regulation or amendments thereto for the purpose of EU vehicle type-approval, the Commission shall adopt a delegated act in accordance with Article 71 in order to make the UNECE regulation or amendments thereto compulsory and to amend Annex I to this Regulation or to amend the delegated acts adopted pursuant to this Regulation, as appropriate. That delegated act shall...
- Target text: Article 71 Exercise of the delegation 1.   The power to adopt the delegated acts is conferred on the Commission subject to the conditions laid down in this Article. 2.   The power to adopt delegated acts referred to in Article 17(5), Article 18(4), Article 19(6), Article 20(8), Article 27(6), Article 28(6), Article 45(4), Article 49(3), Article 53(12), Article 61 and Article 70 shall be conferred on the Commission for a period of five years from 22 March 2013. 3.   The delegation of power referred to in Article 17(5), Article 18(4), Article 19(6), Article 20(8), Article 27(6), Article 28(6), A

## 033 [WITHIN] `Article 60(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32012Q0929(01)` / `29.2`
- Target act/path: `32012Q0929(01)` / `60.3`
- Source context: ...2.   Where a Chamber to which a case has been assigned requests the Court, pursuant to Article 60(3) of these Rules, to assign the case to a formation composed of a greater number of Judges, that formation shall include the members of the Chamber which has referred the case back. ...
- Target text: 3.   The formation to which a case has been assigned may, at any stage of the proceedings, request the Court to assign the case to a formation composed of a greater number of Judges.

## 034 [WITHIN] `Article 34(7)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R0696` / `24.4.c`
- Target act/path: `32021R0696` / `34.7`
- Source context: ...(c) the legal entity complies with Article 34(7). ...
- Target text: 7.   The entities involved in the Programme shall take all the necessary measures, including in light of the issues identified in the risk analysis, to ensure the security of the Programme.

## 035 [WITHIN] `Article 3`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R0887` / `4.1`
- Target act/path: `32021R0887` / `3`
- Source context: ...1.   The Competence Centre shall have the overall objective of promoting research, innovation and deployment in the area of cybersecurity in order to fulfil the mission as set out in Article 3. ...
- Target text: Article 3 Mission of the Competence Centre and the Network 1.   The mission of the Competence Centre and the Network is to help the Union to: (a) strengthen its leadership and strategic autonomy in the area of cybersecurity by retaining and developing the Union’s research, academic, societal, technological and industrial cybersecurity capacities and capabilities necessary to enhance trust and security, including the confidentiality, integrity and accessibility of data, in the Digital Single Market; (b) support Union technological capacities, capabilities and skills in relation to the resilienc

## 036 [WITHIN] `paragraph 3`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `32014R0909` / `23.7`
- Target act/path: `32014R0909` / `23.3`
- Source context: ...7.   In the event of a change in any of the information communicated in accordance with paragraph 3, a CSD shall give written notice of that change to the competent authority of the home Member State at least one month before implementing the change. The competent authority of the host Member State shall also be infor...
- Target text: 3.   Any CSD wishing to provide the services referred to in paragraph 2 within the territory of another Member State for the first time, or to change the range of those services provided shall communicate the following information to the competent authority of the home Member State: (a) the Member State in which the CSD intends to operate; (b) a programme of operations stating in particular the services which the CSD intends to provide; (c) the currency or currencies that the CSD intends to process; (d) where there is a branch, the organisational structure of the branch and the names of those

## 037 [WITHIN] `(a) of Article 36(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R1305` / `37.1`
- Target act/path: `32013R1305` / `36.1.a`
- Source context: ...1.   Support under point (a) of Article 36(1) shall only be granted for insurance contracts which cover for loss caused by an adverse climatic event, or by an animal or plant disease, or a pest infestation, or an environmental incident or a measure adopted in accor...
- Target text: (a) financial contributions to premiums for crop, animal and plant insurance against economic losses to farmers caused by adverse climatic events, animal or plant diseases, pest infestation, or an environmental incident;

## 038 [WITHIN] `or 34`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0508` / `95.2.e`
- Target act/path: `32014R0508` / `34`
- Source context: ...(e) the operation is related to support under Article 33 or 34 or to compensation under Article 54, 55 or 56; ...
- Target text: Article 34 Permanent cessation of fishing activities 1.   The EMFF may support measures for the permanent cessation of fishing activities only when that is achieved through the scrapping of fishing vessels and provided that: (a) such scrapping is included in the operational programme referred to in Article 18; and (b) the permanent cessation is foreseen as a tool of an action plan referred to in Article 22(4) of Regulation (EU) No 1380/2013 indicating that the fleet segment is not effectively balanced with the fishing opportunities available to that segment. 2.   Support under paragraph 1 shal

## 039 [WITHIN] `paragraph 3`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `32006L0118` / `5.4.b`
- Target act/path: `32006L0118` / `5.3`
- Source context: ...(b) the reasons for the starting points defined pursuant to paragraph 3. ...
- Target text: 3.   Member States shall define the starting point for trend reversal as a percentage of the level of the groundwater quality standards set out in Annex I and of the threshold values established pursuant to Article 3, on the basis of the identified trend and the environmental risk associated therewith, in accordance with Part B, point 1 of Annex IV.

## 040 [WITHIN] `Article 8(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32009L0119` / `7.4`
- Target act/path: `32009L0119` / `8.1`
- Source context: ...4.   Each Member State having a CSE shall require it, for the purposes of Article 8(1) and (2), to publish: (a) on an ongoing basis, full information, broken down by product category, on the stock volumes that it can undertake to maintain for economic operators, or, where appropriate, interested CSEs; (b)...
- Target text: 1.   Each Member State shall ensure that any economic operator on which it imposes stockholding obligations in order to fulfil its obligations under Article 3 is given the right to delegate those obligations at least in part and at the choice of the economic operator, but only to: (a) the CSE of the Member State on whose account such stocks are held; (b) one or more other CSEs which have in advance declared themselves willing to hold such stocks, provided that such delegations have been authorised in advance both by the Member State on whose account such stocks are held and by all Member State

## 041 [WITHIN] `Articles 3 to 7`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32019L0713` / `8.1`
- Target act/path: `32019L0713` / `3`
- Source context: ...1.   Member States shall take the necessary measures to ensure that inciting or aiding and abetting an offence referred to in Articles 3 to 7 is punishable as a criminal offence. ...
- Target text: Article 3 Fraudulent use of non-cash payment instruments Member States shall take the necessary measures to ensure that, when committed intentionally, the following conduct is punishable as a criminal offence: (a) the fraudulent use of a stolen or otherwise unlawfully appropriated or obtained non-cash payment instrument; (b) the fraudulent use of a counterfeit or falsified non-cash payment instrument.

## 042 [WITHIN] `paragraph 1`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `22021A0430(01)` / `556.2`
- Target act/path: `22021A0430(01)` / `556.1`
- Source context: ...2.   As an exception to point (e) of paragraph 1, the United Kingdom competent authority may transfer PNR data to a third country if: (a) the head of that authority, or a senior official specifically mandated by the head, considers that the disclosure is necessary for...
- Target text: 1.   The United Kingdom shall ensure that the United Kingdom competent authority does not disclose PNR data to public authorities in third countries unless all the following conditions are met: (a) the PNR data is disclosed to public authorities whose functions are directly related to the purposes set out in Article 544; (b) the PNR data is disclosed only on a case-by-case basis; (c) the PNR data is disclosed only if necessary for the purposes set out in Article 544; (d) only the minimum amount of PNR data necessary is disclosed; and (e) the third country to which the PNR data is disclosed has

## 043 [WITHIN] `(h) of Article 21`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0514` / `48`
- Target act/path: `32014R0514` / `21.h`
- Source context: ...Article 48 Obligations of Member States A financial correction by the Commission shall not prejudice the Member State’s obligation to pursue recoveries under point (h) of Article 21 of this Regulation and to recover State aid within the meaning of Article 107(1) TFEU and under Article 14 of Council Regulation (EC) No 659/1999 (12). ...
- Target text: (h) the prevention, detection and correction of irregularities, including fraud, and the recovery of amounts unduly paid, together with any interest on late payments.

## 044 [WITHIN] `Article 8(2)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019L0770` / `11.2`
- Target act/path: `32019L0770` / `8.2`
- Source context: ... for a single act of supply or a series of individual acts of supply, the trader shall be liable for any lack of conformity under Articles 7, 8 and 9 which exists at the time of supply, without prejudice to point (b) of Article 8(2). If, under national law, the trader is only liable for a lack of conformity that becomes apparent within a period of time after supply, that period shall not be less than two years from the time of supply, without preju...
- Target text: 2.   The trader shall ensure that the consumer is informed of and supplied with updates, including security updates, that are necessary to keep the digital content or digital service in conformity, for the period of time: (a) during which the digital content or digital service is to be supplied under the contract, where the contract provides for a continuous supply over a period of time; or (b) that the consumer may reasonably expect, given the type and purpose of the digital content or digital service and taking into account the circumstances and nature of the contract, where the contract pro

## 045 [WITHIN] `Article 29(2)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32016R0399` / `30.2`
- Target act/path: `32016R0399` / `29.2`
- Source context: ...2.   Before adopting a proposal for a Council recommendation, in accordance with Article 29(2), the Commission may: (a) request Member States, the Agency, Europol or other Union bodies, offices or agencies to provide it with further information; (b) carry out on-site visits, with the support of experts from Membe...
- Target text: 2.   The Council may, as a last resort and as a measure to protect the common interests within the area without internal border control, where all other measures, in particular those referred to in Article 21(1), are ineffective in mitigating the serious threat identified, recommend that one or more Member States decide to reintroduce border control at all or at specific parts of their internal borders. The Council’s recommendation shall be based on a proposal from the Commission. The Member States may request the Commission to submit such a proposal to the Council for a recommendation. In its

## 046 [WITHIN] `Article 66(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019L0944` / `35`
- Target act/path: `32019L0944` / `66.3`
- Source context: ...prevent the operation of a combined transmission and distribution system operator, provided that the operator complies with Article 43(1), Articles 44 and 45, or Section 3 of Chapter VI, or that the operator falls under Article 66(3). CHAPTER V GENERAL RULES APPLICABLE TO TRANSMISSION SYSTEM OPERATORS ...
- Target text: 3.   Article 43 shall not apply to Cyprus, Luxembourg and Malta. In addition, Articles 6 and 35 shall not apply to Malta and Articles 44, 45, 46, 47, 48, 49, 50 and 52 shall not apply to Cyprus. For the purposes of point (b) of Article 43(1), the notion ‘undertaking performing any of the functions of generation or supply’ shall not include final customers who perform any of the functions of generation and/or supply of electricity, either directly or via undertakings over which they exercise control, either individually or jointly, provided that the final customers including their shares of the

## 047 [WITHIN] `paragraph 1`
- Resolution: `relative`; keyword: `paragraph`
- Source act/path: `32015R0848` / `3.3`
- Target act/path: `32015R0848` / `3.1`
- Source context: ...3.   Where insolvency proceedings have been opened in accordance with paragraph 1, any proceedings opened subsequently in accordance with paragraph 2 shall be secondary insolvency proceedings. ...
- Target text: 1.   The courts of the Member State within the territory of which the centre of the debtor's main interests is situated shall have jurisdiction to open insolvency proceedings (‘main insolvency proceedings’). The centre of main interests shall be the place where the debtor conducts the administration of its interests on a regular basis and which is ascertainable by third parties. In the case of a company or legal person, the place of the registered office shall be presumed to be the centre of its main interests in the absence of proof to the contrary. That presumption shall only apply if the re

## 048 [WITHIN] `Article 8`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0575` / `21.1`
- Target act/path: `32013R0575` / `8`
- Source context: ... a Member State shall do everything within their power to reach a joint decision on whether the conditions in points (a) to (d) of Article 8(1) are met and identifying a single liquidity sub-group for the application of Article 8. The joint decision shall be reached within six months after submission by the consolidating supervisor of a report identifying single liquidity sub-groups on the basis of the criteria laid down in Article 8. In the eve...
- Target text: Article 8 Derogation to the application of liquidity requirements on an individual basis 1.   The competent authorities may waive in full or in part the application of Part Six to an institution and to all or some of its subsidiaries in the Union and supervise them as a single liquidity sub-group so long as they fulfil all of the following conditions: (a) the parent institution on a consolidated basis or a subsidiary institution on a sub-consolidated basis complies with the obligations laid down in Part Six; (b) the parent institution on a consolidated basis or the subsidiary institution on a

## 049 [WITHIN] `, 35 to 54`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32019R0006` / `2.5`
- Target act/path: `32019R0006` / `50`
- Source context: ...5.   By way of derogation from paragraph 1 of this Article, Articles 5 to 15, 17 to 33, 35 to 54, 57 to 72, 82 to 84, 95, 98, 106, 107, 110, 112 to 116, 128, 130 and 136 shall not apply to homeopathic veterinary medicinal products which are registered in accordance with Article 86. ...
- Target text: Article 50 Request by the applicant for re-examination of the assessment report 1.   Within 15 days of receipt of the assessment report referred to in Article 49(5), the applicant may provide written notice to the competent authority in the reference Member State requesting a re-examination of the assessment report. In that case, the applicant shall forward to the competent authority in the reference Member State detailed grounds for such a request within 60 days of receipt of that assessment report. The competent authority in the reference Member State shall without delay forward that request

## 050 [CROSS] `Article 32(2)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32012R0648` / `21.6.b`
- Target act/path: `32010R1095` / `32.2`
- Source context: ...(b) initiate and coordinate Union-wide assessments of the resilience of CCPs to adverse market developments in accordance with Article 32(2) of Regulation (EU) No 1095/2010. Where an assessment referred to in point (b) of the second subparagraph exposes shortcomings in the resilience of one or more CCPs, ESMA shall issue the necessary recommendations pursuan...
- Target text: 2.   The Authority shall, in cooperation with the ESRB, initiate and coordinate Union-wide assessments of the resilience of financial market participants to adverse market developments. To that end, it shall develop the following, for application by the competent authorities: (a) common methodologies for assessing the effect of economic scenarios on the financial position of a financial market participant; (b) common approaches to communication on the outcomes of these assessments of the resilience of financial market participants; (c) common methodologies for assessing the effect of particula

## 051 [CROSS] `Article 9(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019R1241` / `annex-zone.chunk 22`
- Target act/path: `32010R1236` / `9.1`
- Source context: ...oard. 3.3. The conversion factor to be applied to the gutted and headed presentation, including the Japanese cut presentation, of redfish caught in this fishery shall be 1,70. 3.4. By way of derogation from point (b) of Article 9(1) of Regulation (EU) No 1236/2010, masters of fishing vessels engaged in this fishery shall report their catches on a daily basis. 3.5. In addition to Article 5 of Regulation (EU) No 1236/2010, an authorisation to fish fo...
- Target text: 1.   The masters of EU fishing vessels engaged in fishing activities carried out in respect of regulated resources shall communicate catch reports by electronic means to their Fisheries Monitoring Centre, as defined in point (15) of Article 4 of Regulation (EC) No 1224/2009. The data contained in such reports shall be accessible to the Commission on request. Reports shall include the following: (a) reports on the quantities held on board when entering the Regulatory Area. Such reports shall be transmitted no earlier than 12 hours and no later than 2 hours before each entry into the Regulatory

## 052 [CROSS] `Article 32(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0537` / `30.2`
- Target act/path: `32006L0043` / `32.1`
- Source context: ...2.   The CEAOB shall be composed of one member from each Member State who shall be high level representatives from the competent authorities referred to in Article 32(1) of Directive 2006/43/EC, and one member appointed by the ESMA, hereinafter referred to as ‘members’. ...
- Target text: 1.   Member States shall organise an effective system of public oversight for statutory auditors and audit firms based on the principles set out in paragraphs 2 to 7.

## 053 [CROSS] `Article 92`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013L0036` / `133.3`
- Target act/path: `32013R0575` / `92`
- Source context: ...3.   For the purpose of paragraph 1, institutions may be required to maintain, in addition to the Common Equity Tier 1 capital maintained to meet the own funds requirement imposed by Article 92 of Regulation (EU) No 575/2013, a systemic risk buffer of Common Equity Tier 1 capital of at least 1 % based on the exposures to which the systemic risk buffer applies in accordance with paragraph 8 of this Article, on ...
- Target text: Article 92 Own funds requirements 1.   Subject to Articles 93 and 94, institutions shall at all times satisfy the following own funds requirements: (a) a Common Equity Tier 1 capital ratio of 4,5 %; (b) a Tier 1 capital ratio of 6 %; (c) a total capital ratio of 8 %. 2.   Institutions shall calculate their capital ratios as follows: (a) the Common Equity Tier 1 capital ratio is the Common Equity Tier 1 capital of the institution expressed as a percentage of the total risk exposure amount; (b) the Tier 1 capital ratio is the Tier 1 capital of the institution expressed as a percentage of the tot

## 054 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32012R0648` / `34.3`
- Target act/path: `32010R1095` / `11`
- Source context: ...hose draft regulatory technical standards to the Commission by 30 September 2012. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1095/2010. ...
- Target text: Article 11 Exercise of the delegation 1.   The power to adopt regulatory technical standards referred to in Article 10 shall be conferred on the Commission for a period of 4 years from 16 December 2010. The Commission shall draw up a report in respect of the delegated power not later than 6 months before the end of the four-year period. The delegation of power shall be automatically extended for periods of an identical duration, unless the European Parliament or the Council revokes it in accordance with Article 14. 2.   As soon as it adopts a regulatory technical standard, the Commission shall

## 055 [CROSS] `Article 93(7)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32010L0044` / `32.1`
- Target act/path: `32009L0065` / `93.7`
- Source context: ...1.   Competent authorities shall designate an e-mail address for the purpose of receiving notification of updates and amendments to the documents referred to in Article 93(2) of Directive 2009/65/EC, pursuant to Article 93(7) of that Directive. ...
- Target text: 7.   The UCITS home Member State shall ensure that the competent authorities of the UCITS host Member State have access, by electronic means, to the documents referred to in paragraph 2 and, if applicable, to any translations thereof. It shall ensure that the UCITS keeps those documents and translations up to date. The UCITS shall notify any amendments to the documents referred to in paragraph 2 to the competent authorities of the UCITS host Member State and shall indicate where those documents can be obtained electronically.

## 056 [CROSS] `and 265`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32019R2152` / `annex-zone.chunk 5`
- Target act/path: `32006L0112` / `265`
- Source context: ...goods in accordance with point (c) of Article 251 of that Directive; (b) information from recapitulative statements on intra-Union supplies collected from the recapitulative VAT statements in accordance with Articles 264 and 265 of Directive 2006/112/EC; (c) information on intra-Union acquisitions communicated by all other Member States in accordance with Article 21(2) of Council Regulation (EU) No 904/2010 (1). (1)  Council Regulation (EU) No...
- Target text: Article 265 1.   In the case of intra-Community acquisitions of goods, as referred to in Article 42, the taxable person identified for VAT purposes in the Member State which issued him with the VAT identification number under which he made such acquisitions shall set the following information out clearly on the recapitulative statement: (a) his VAT identification number in that Member State and under which he made the acquisition and subsequent supply of goods; (b) the VAT identification number, in the Member State in which dispatch or transport of the goods ended, of the person to whom the su

## 057 [CROSS] `Article 7`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019R0942` / `14.1`
- Target act/path: `32009R0715` / `7`
- Source context: ...idelines in accordance with Article 59 of Regulation (EU) 2019/943 or Article 6 of Regulation (EC) No 715/2009, and in the process of proposing amendments of network codes under Article 60 of Regulation (EU) 2019/943 or Article 7 of Regulation (EC) No 715/2009 ACER shall, extensively consult at an early stage market participants, transmission system operators, consumers, end-users and, where relevant, competition authorities, without prejudice t...
- Target text: Article 7 Amendments of network codes 1.   Draft amendments to any network code adopted under Article 6 may be proposed to the Agency by persons who are likely to have an interest in that network code, including the ENTSO for Gas, transmission system operators, network users and consumers. The Agency may also propose amendments of its own initiative. 2.   The Agency shall consult all stakeholders in accordance with Article 10 of Regulation (EC) No 713/2009. Following this process, the Agency may make reasoned proposals for amendments to the Commission, explaining how such proposals are consist

## 058 [CROSS] `Article 17`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R1056` / `0`
- Target act/path: `32020R0852` / `17`
- Source context: ...il (8). In this context the JTF should support activities that respect the climate and environmental standards and priorities of the Union and do no significant harm to the environmental objectives within the meaning of Article 17 of Regulation (EU) 2020/852 of the European Parliament and of the Council (9), and that ensure the transition towards a low carbon economy in the pathway to achieving a climate-neutral Union by 2050. (7) The resources f...
- Target text: Article 17 Significant harm to environmental objectives 1.   For the purposes of point (b) of Article 3, taking into account the life cycle of the products and services provided by an economic activity, including evidence from existing life-cycle assessments, that economic activity shall be considered to significantly harm: (a) climate change mitigation, where that activity leads to significant greenhouse gas emissions; (b) climate change adaptation, where that activity leads to an increased adverse impact of the current climate and the expected future climate, on the activity itself or on peo

## 059 [CROSS] `Article 25`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32017R1001` / `25`
- Target act/path: `32012R1215` / `25`
- Source context: ...Article 25 of Regulation (EU) No 1215/2012 shall apply if the parties agree that a different EU trade mark court shall have jurisdiction; (b) ...
- Target text: Article 25 1.   If the parties, regardless of their domicile, have agreed that a court or the courts of a Member State are to have jurisdiction to settle any disputes which have arisen or which may arise in connection with a particular legal relationship, that court or those courts shall have jurisdiction, unless the agreement is null and void as to its substantive validity under the law of that Member State. Such jurisdiction shall be exclusive unless the parties have agreed otherwise. The agreement conferring jurisdiction shall be either: (a) in writing or evidenced in writing; (b) in a form

## 060 [CROSS] `Article 2`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32016R2336` / `1`
- Target act/path: `32013R1380` / `2`
- Source context: ...Article 1 Objectives This Regulation shall contribute to the achievement of the objectives listed in Article 2 of Regulation (EU) No 1380/2013 as far as deep-sea species and habitats are concerned. In addition, it shall aim at: (a) improving scientific knowledge on deep-sea species and their habitats; (b) preventing significant ...
- Target text: Article 2 Objectives 1.   The CFP shall ensure that fishing and aquaculture activities are environmentally sustainable in the long-term and are managed in a way that is consistent with the objectives of achieving economic, social and employment benefits, and of contributing to the availability of food supplies. 2.   The CFP shall apply the precautionary approach to fisheries management, and shall aim to ensure that exploitation of living marine biological resources restores and maintains populations of harvested species above levels which can produce the maximum sustainable yield. In order to

## 061 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32013R0575` / `18.7`
- Target act/path: `32010R1093` / `14`
- Source context: ...those draft regulatory technical standards to the Commission by 31 December 2016. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1093/2010. ...
- Target text: Article 14 Non-endorsement or amendment of draft regulatory technical standards 1.   In the event that the Commission does not endorse a draft regulatory technical standard or amends it as provided for in Article 10, the Commission shall inform the Authority, the European Parliament and the Council, stating its reasons. 2.   Where appropriate, the European Parliament or the Council may invite the responsible Commissioner, together with the Chairperson of the Authority, within 1 month of the notice referred to in paragraph 1, for an ad hoc meeting of the competent committee of the European Parl

## 062 [CROSS] `Article 25`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019R1122` / `3.7`
- Target act/path: `32003L0087` / `25`
- Source context: ...tion allowances’ means allowances created pursuant to Article 3c(2) of Directive 2003/87/EC, including allowances, created for the same purpose, stemming from emission trading systems that are linked to the EU ETS under Article 25 of that Directive; ...
- Target text: Article 25 Links with other greenhouse gas emissions trading schemes 1.   Agreements should be concluded with third countries listed in Annex B to the Kyoto Protocol which have ratified the Protocol to provide for the mutual recognition of allowances between the Community scheme and other greenhouse gas emissions trading schemes in accordance with the rules set out in Article 300 of the Treaty. 2.   Where an agreement referred to in paragraph 1 has been concluded, the Commission shall draw up any necessary provisions relating to the mutual recognition of allowances under that agreement in acco

## 063 [CROSS] `Articles 1 to 10`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0054` / `3.1`
- Target act/path: `32011R0492` / `4`
- Source context: ...at after possible recourse to other competent authorities including, where they deem it to be appropriate, conciliation procedures, judicial procedures, for the enforcement of obligations under Article 45 TFEU and under Articles 1 to 10 of Regulation (EU) No 492/2011, are available to all Union workers and members of their family who consider that they have suffered or are suffering from unjustified restrictions and obstacles to their right to free mov...
- Target text: Article 4 1.   Provisions laid down by law, regulation or administrative action of the Member States which restrict by number or percentage the employment of foreign nationals in any undertaking, branch of activity or region, or at a national level, shall not apply to nationals of the other Member States. 2.   When in a Member State the granting of any benefit to undertakings is subject to a minimum percentage of national workers being employed, nationals of the other Member States shall be counted as national workers, subject to Directive 2005/36/EC of the European Parliament and of the Counc

## 064 [CROSS] `Article 19`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32012R1215` / `28.3`
- Target act/path: `32007R1393` / `19`
- Source context: ...3.   Article 19 of Regulation (EC) No 1393/2007 of the European Parliament and of the Council of 13 November 2007 on the service in the Member States of judicial and extrajudicial documents in civil or commercial matters (service of do...
- Target text: Article 19 Defendant not entering an appearance 1.   Where a writ of summons or an equivalent document has had to be transmitted to another Member State for the purpose of service under the provisions of this Regulation and the defendant has not appeared, judgment shall not be given until it is established that: (a) the document was served by a method prescribed by the internal law of the Member State addressed for the service of documents in domestic actions upon persons who are within its territory; or (b) the document was actually delivered to the defendant or to his residence by another me

## 065 [CROSS] `Article 69(7)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R1057` / `8.2`
- Target act/path: `32021R1060` / `69.7`
- Source context: ...2.   In accordance with Article 69(7) of Regulation (EU) 2021/1060, Member States shall ensure the effective examination of complaints. This is without prejudice to the general possibility of citizens and stakeholders to address complaints to the Commission...
- Target text: 7.   Member States shall make arrangements to ensure the effective examination of complaints concerning the Funds. The scope, rules and procedures concerning those arrangements shall be the responsibility of Member States in accordance with their institutional and legal framework. This is without prejudice to the general possibility to address complaints to the Commission by citizens and stakeholders. Member States shall, upon request by the Commission, examine complaints submitted to the Commission falling within the scope of their programmes and shall inform the Commission of the results of

## 066 [CROSS] `Article 1(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R0784` / `1.5`
- Target act/path: `32010L0013` / `1.1`
- Source context: ...5.   This Regulation shall be without prejudice to Directives 2000/31/EC and 2010/13/EU. For audiovisual media services as defined in point (a) of Article 1(1) of Directive 2010/13/EU, Directive 2010/13/EU shall prevail. ...
- Target text: 1.   For the purposes of this Directive, the following definitions shall apply: (a) ‘audiovisual media service’ means: (i) a service as defined by Articles 56 and 57 of the Treaty on the Functioning of the European Union which is under the editorial responsibility of a media service provider and the principal purpose of which is the provision of programmes, in order to inform, entertain or educate, to the general public by electronic communications networks within the meaning of point (a) of Article 2 of Directive 2002/21/EC. Such an audiovisual media service is either a television broadcast a

## 067 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0065` / `12.8`
- Target act/path: `32010R1095` / `10`
- Source context: ...t those draft regulatory technical standards to the Commission by 1 January 2014. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1095/2010. ...
- Target text: Article 10 Regulatory technical standards 1.   Where the European Parliament and the Council delegate power to the Commission to adopt regulatory technical standards by means of delegated acts under Article 290 TFEU in order to ensure consistent harmonisation in the areas specifically set out in the legislative acts referred to in Article 1(2), the Authority may develop draft regulatory technical standards. The Authority shall submit its draft standards to the Commission for endorsement. Regulatory technical standards shall be technical, shall not imply strategic decisions or policy choices an

## 068 [CROSS] `Article 33(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32018R0848` / `57.2`
- Target act/path: `32007R0834` / `33.3`
- Source context: ...2.   The Commission shall, by means of an implementing act, establish a list of the control authorities and control bodies recognised under Article 33(3) of Regulation (EC) No 834/2007, and may amend that list by means of implementing acts. Those implementing acts shall be adopted in accordance with the examination procedure referred to in Article 55(2). ...
- Target text: 3.   For products not imported under Article 32 and not imported from a third country which is recognised under paragraph 2 of this Article, the Commission may, in accordance with the procedure referred to in Article 37(2), recognise the control authorities and control bodies, including control authorities and control bodies as referred to in Article 27, competent to carry out controls and issue certificates in third countries for the purpose of paragraph 1, and establish a list of these control authorities and control bodies. The assessment of equivalency shall take into account Codex Aliment

## 069 [CROSS] `Article 19(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32012R0236` / `23.4`
- Target act/path: `32010R1095` / `19.3`
- Source context: ...liation shall be completed before midnight at the end of the same trading day. If the competent authorities concerned fail to reach an agreement within the conciliation phase, ESMA may take a decision in accordance with Article 19(3) of Regulation (EU) No 1095/2010. The decision shall be taken before the opening of the next trading day. ...
- Target text: 3.   If the competent authorities concerned fail to reach an agreement within the conciliation phase referred to in paragraph 2, the Authority may, in accordance with the procedure set out in the third and fourth subparagraph of Article 44(1) take a decision requiring them to take specific action or to refrain from action in order to settle the matter, with binding effects for the competent authorities concerned, in order to ensure compliance with Union law.

## 070 [CROSS] `Articles 1 to 10N`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `42012D0750` / `0`
- Target act/path: `31993L0013` / `1`
- Source context: ...mental noiseApplicable provisions: Articles 1 to 16, Annexes I to IVE. CONSUMER PROTECTIONNo 90/314Council Directive 90/314/EEC of 13 June 1990 on package travel, package holidays and package toursApplicable provisions: Articles 1 to 10No 93/13Council Directive 93/13/EEC of 5 April 1993 on unfair terms in consumer contractsApplicable provisions: Articles 1 to 10 and AnnexNo 95/46Directive 95/46/EC of the European Parliament and of the Council of 24 Octo...
- Target text: Article 1 1.   The purpose of this Directive is to approximate the laws, regulations and administrative provisions of the Member States relating to unfair terms in contracts concluded between a seller or supplier and a consumer. 2.   The contractual terms which reflect mandatory statutory or regulatory provisions and the provisions or principles of international conventions to which the Member States or the Community are party, particularly in the transport area, shall not be subject to the provisions of this Directive.

## 071 [CROSS] `Articles 16 to 29`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0030` / `15`
- Target act/path: `32008R0765` / `22`
- Source context: ...Article 15(3) and Articles 16 to 29 of Regulation (EC) No 765/2008 shall apply to apparatus. ...
- Target text: Article 22 Exchange of information — Community Rapid Information System 1.   Where a Member State takes or intends to take a measure in accordance with Article 20 and considers that the reasons which prompted the measure or the effects of the measure go beyond its territory, it shall immediately notify the Commission of that measure, in accordance with paragraph 4 of this Article. It shall also inform the Commission without delay of the modification or withdrawal of any such measure. 2.   If a product presenting a serious risk has been made available on the market, Member States shall notify t

## 072 [CROSS] `Article 25`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32017R1004` / `1.1`
- Target act/path: `32013R1380` / `25`
- Source context: ...rticle 2 of Regulation (EU) No 1380/2013, this Regulation establishes rules on the collection, management and use of biological, environmental, technical and socioeconomic data in the fisheries sector as provided for in Article 25 of Regulation (EU) No 1380/2013. ...
- Target text: Article 25 Data requirements for fisheries management 1.   Member States shall, in accordance with the rules adopted in the area of data collection, collect biological, environmental, technical, and socio-economic data necessary for fisheries management, manage those data and make them available to end–users, including bodies designated by the Commission. The acquisition and management of such data shall be eligible for funding through the European Maritime and Fisheries Fund in accordance with a future Union legal act establishing the conditions for the financial support for maritime and fish

## 073 [CROSS] `Article 16`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014L0059` / `65.5`
- Target act/path: `32010R1093` / `16`
- Source context: ...5.   EBA shall, by 3 July 2015, issue guidelines in accordance with Article 16 of Regulation (EU) No 1093/2010 to specify the minimum list of services or facilities that are necessary to enable a recipient to effectively operate a business transferred to it. ...
- Target text: Article 16 Guidelines and recommendations 1.   The Authority shall, with a view to establishing consistent, efficient and effective supervisory practices within the ESFS, and to ensuring the common, uniform and consistent application of Union law, issue guidelines and recommendations addressed to competent authorities or financial institutions. 2.   The Authority shall, where appropriate, conduct open public consultations regarding the guidelines and recommendations and analyse the related potential costs and benefits. Such consultations and analyses shall be proportionate in relation to the s

## 074 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0065` / `32.2`
- Target act/path: `32010R1095` / `13`
- Source context: ...bmit those draft regulatory technical standards to the Commission by 3 July 2015. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1095/2010. ...
- Target text: Article 13 Objections to regulatory technical standards 1.   The European Parliament or the Council may object to a regulatory technical standard within a period of 3 months from the date of notification of the regulatory technical standard adopted by the Commission. At the initiative of the European Parliament or the Council that period shall be extended by 3 months. Where the Commission adopts a regulatory technical standard which is the same as the draft regulatory technical standard submitted by the Authority, the period during which the European Parliament and the Council may object shall

## 075 [CROSS] `Article 30(3)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32016R0127` / `7.3`
- Target act/path: `32011R1169` / `30.3`
- Source context: ...3.   By way of derogation from Article 30(3) of Regulation (EU) No 1169/2011, the information included in the mandatory nutrition declaration for infant formula and follow-on formula shall not be repeated on the labelling. ...
- Target text: 3.   Where the labelling of a prepacked food provides the mandatory nutrition declaration referred to in paragraph 1, the following information may be repeated thereon: (a) the energy value; or (b) the energy value together with the amounts of fat, saturates, sugars, and salt.

## 076 [CROSS] `Article 14`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0389` / `42.2`
- Target act/path: `32010R1031` / `14`
- Source context: ...2.   In case of adjustments to the annual volumes in accordance with Article 14 of Regulation (EU) No 1031/2010, the central administrator shall transfer a corresponding quantity of general allowances from the EU Total Quantity Account to the EU Auction Account, or from the EU Auction Account to th...
- Target text: Article 14 Adjustments of the auction calendar 1.   The determinations and publications of the annual volumes to be auctioned and of the bidding windows, volumes, dates, auctioned product, payment and delivery dates in connection with individual auctions pursuant to Articles 10 to 13 and Article 32(4) shall not be modified except for adjustments due to any of the following: (a) the cancellation of an auction pursuant to Article 7(5) and (6), Article 9 and Article 32(5); (b) any suspension of an auction platform other than the auction platforms appointed pursuant to Article 26(1) or (2) of this

## 077 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32012R0648` / `81.5`
- Target act/path: `32010R1095` / `11`
- Source context: ...hose draft regulatory technical standards to the Commission by 30 September 2012. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1095/2010. ...
- Target text: Article 11 Exercise of the delegation 1.   The power to adopt regulatory technical standards referred to in Article 10 shall be conferred on the Commission for a period of 4 years from 16 December 2010. The Commission shall draw up a report in respect of the delegated power not later than 6 months before the end of the four-year period. The delegation of power shall be automatically extended for periods of an identical duration, unless the European Parliament or the Council revokes it in accordance with Article 14. 2.   As soon as it adopts a regulatory technical standard, the Commission shall

## 078 [CROSS] `(e) of Article 8(2)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0288` / `annex-zone.chunk 19`
- Target act/path: `32013R1299` / `8.2.e`
- Source context: ...tive at cooperation programme and operation level. <7.3 type=‘S’ maxlength=‘5500’ input=‘M’ decision=N> SECTION 9 SEPARATE ELEMENTS 9.1.   Major projects to be implemented during the programming period (Reference: point (e) of Article 8(2) of Regulation (EU) No 1299/2013) Table 23 List of major projects (22) Project Planned notification/submission date (year, quarter) Planned start of implementation (year, quarter) Planned completion date (year quarter) P...
- Target text: (e) a list of major projects for which the implementation is planned during the programming period. The Commission shall adopt implementing acts concerning the nomenclature referred to in points (b)(vii) and (c)(v) of the first subparagraph. Those implementing acts shall be adopted in accordance with the examination procedure referred to in Article 150(3) of Regulation (EU) No 1303/2000.

## 079 [CROSS] `Article 11(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019Q1122(01)` / `0`
- Target act/path: `32014R1141` / `11.1`
- Source context: ...cision shall be deemed to have been adopted. 5. On the basis of a proposal by the committee responsible, the Conference of Presidents shall appoint two members of the committee of independent eminent persons pursuant to Article 11(1) of Regulation (EU, Euratom) No 1141/2014. TITLE XIII APPLICATION AND AMENDMENT OF THE RULES OF PROCEDURE Rule 236 Application of the Rules of Procedure 1. If doubt arises over the application or interpretation of these ...
- Target text: 1.   A committee of independent eminent persons is hereby established. It shall consist of six members, with the European Parliament, the Council and the Commission each appointing two members. The members of the committee shall be selected on the basis of their personal and professional qualities. They shall neither be members of the European Parliament, the Council or the Commission, nor hold any electoral mandate, be officials or other servants of the European Union or be current or former employees of a European political party or a European political foundation. Members of the committee s

## 080 [CROSS] `Article 2(1)(a)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0609` / `0`
- Target act/path: `32014D0335` / `2.1.a`
- Source context: ...s and accordingly rules should be laid down for the Member States to provide the Commission with those own resources. This Regulation takes over the rules on making available the traditional own resources referred to in Article 2(1)(a) of Decision 2014/335/EU, Euratom, the own resources based on value added tax (VAT) referred to in Article 2(1)(b) of that Decision (‘VAT-based own resource’) and own resources based on gross national income (GNI) referr...
- Target text: (a) traditional own resources consisting of levies, premiums, additional or compensatory amounts, additional amounts or factors, Common Customs Tariff duties and other duties established or to be established by the institutions of the Union in respect of trade with third countries, customs duties on products under the expired Treaty establishing the European Coal and Steel Community, as well as contributions and other duties provided for within the framework of the common organisation of the markets in sugar;

## 081 [CROSS] `Article 19`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32011L0061` / `37.9`
- Target act/path: `32010R1095` / `19`
- Source context: ...paragraph by the competent authorities of the Member State of reference of the AIFM, the competent authorities concerned may refer the matter to the ESMA which may act in accordance with the powers conferred on it under Article 19 of Regulation (EU) No 1095/2010. ...
- Target text: Article 19 Settlement of disagreements between competent authorities in cross-border situations 1.   Without prejudice to the powers laid down in Article 17, where a competent authority disagrees about the procedure or content of an action or inaction of a competent authority of another Member State in cases specified in the acts referred to in Article 1(2), the Authority, at the request of one or more of the competent authorities concerned may assist the authorities in reaching an agreement in accordance with the procedure set out in paragraphs 2 to 4 of this Article. In cases specified in th

## 082 [CROSS] `Articles 16 to 29`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0053` / `15`
- Target act/path: `32008R0765` / `27`
- Source context: ...Article 15(3) and Articles 16 to 29 of Regulation (EC) No 765/2008 shall apply to radio equipment. ...
- Target text: Article 27 Controls of products entering the Community market 1.   The authorities of the Member States in charge of the control of products entering the Community market shall have the powers and resources necessary for the proper performance of their tasks. They shall carry out appropriate checks on the characteristics of products on an adequate scale, in accordance with the principles set out in Article 19(1), before those products are released for free circulation. 2.   Where in a Member State more than one authority is responsible for market surveillance or external border controls, those

## 083 [CROSS] `Article 20`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0168` / `10.4`
- Target act/path: `32008R0765` / `20`
- Source context: ...the vehicle, system, component or separate technical unit, in a language which can be easily understood by that authority. Manufacturers shall cooperate with the national authority on any action taken in accordance with Article 20 of Regulation (EC) No 765/2008 to eliminate the risks posed by their vehicles, systems, components or separate technical units which have been placed on the market, registered or entered into service. ...
- Target text: Article 20 Products presenting a serious risk 1.   Member States shall ensure that products which present a serious risk requiring rapid intervention, including a serious risk the effects of which are not immediate, are recalled, withdrawn or that their being made available on their market is prohibited, and that the Commission is informed without delay thereof, in accordance with Article 22. 2.   The decision whether or not a product represents a serious risk shall be based on an appropriate risk assessment which takes account of the nature of the hazard and the likelihood of its occurrence.

## 084 [CROSS] `Articles 16 to 29`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32016R0426` / `15`
- Target act/path: `32008R0765` / `24`
- Source context: ...Article 15(3) and Articles 16 to 29 of Regulation (EC) No 765/2008 shall apply to appliances and fittings covered by this Regulation. ...
- Target text: Article 24 Principles of cooperation between the Member States and the Commission 1.   Member States shall ensure efficient cooperation and exchange of information between their market surveillance authorities and those of the other Member States and between their own authorities and the Commission and the relevant Community agencies regarding their market surveillance programmes and all issues relating to products presenting risks. 2.   For the purposes of paragraph 1, the market surveillance authorities of one Member State shall give the market surveillance authorities of other Member States

## 085 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32013R0575` / `221.9.b`
- Target act/path: `32010R1093` / `10`
- Source context: ...those draft regulatory technical standards to the Commission by 31 December 2015. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1093/2010. ...
- Target text: Article 10 Regulatory technical standards 1.   Where the European Parliament and the Council delegate power to the Commission to adopt regulatory technical standards by means of delegated acts pursuant to Article 290 TFEU in order to ensure consistent harmonisation in the areas specifically set out in the legislative acts referred to in Article 1(2), the Authority may develop draft regulatory technical standards. The Authority shall submit its draft standards to the Commission for endorsement. Regulatory technical standards shall be technical, shall not imply strategic decisions or policy choi

## 086 [CROSS] `, 25`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32012L0019` / `9.2`
- Target act/path: `32008L0098` / `25`
- Source context: ...2.   Exemptions from permit requirements, conditions for exemptions and registration shall be in compliance, respectively, with Articles 24, 25 and 26 of Directive 2008/98/EC. ...
- Target text: Article 25 Conditions for exemptions 1.   Where a Member State wishes to allow exemptions, as provided for in Article 24, it shall lay down, in respect of each type of activity, general rules specifying the types and quantities of waste that may be covered by an exemption, and the method of treatment to be used. Those rules shall be designed to ensure that waste is treated in accordance with Article 13. In the case of disposal operations referred to in point (a) of Article 24 those rules should consider best available techniques. 2.   In addition to the general rules provided for in paragraph

## 087 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32012R0648` / `6.4`
- Target act/path: `32010R1095` / `13`
- Source context: ...such draft regulatory technical standards to the Commission by 30 September 2012. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1095/2010. ...
- Target text: Article 13 Objections to regulatory technical standards 1.   The European Parliament or the Council may object to a regulatory technical standard within a period of 3 months from the date of notification of the regulatory technical standard adopted by the Commission. At the initiative of the European Parliament or the Council that period shall be extended by 3 months. Where the Commission adopts a regulatory technical standard which is the same as the draft regulatory technical standard submitted by the Authority, the period during which the European Parliament and the Council may object shall

## 088 [CROSS] `point 1 of Article 3`
- Resolution: `exact+nested-point`; keyword: `Article`
- Source act/path: `32021R0023` / `2.38`
- Target act/path: `32015R2365` / `3.1`
- Source context: ...(38) ‘trade repository’ means a trade repository as defined in point 2 of Article 2 of Regulation (EU) No 648/2012 or in point 1 of Article 3 of Regulation (EU) 2015/2365 of the European Parliament and of the Council (19); ...
- Target text: (1) ‘trade repository’ means a legal person that centrally collects and maintains the records of SFTs;

## 089 [CROSS] `Article 3(2)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0346` / `2.2`
- Target act/path: `32011L0061` / `3.2`
- Source context: ...2.   Where the total assets under management of managers of qualifying social entrepreneurship fund registered in accordance with Article 15 subsequently exceed the threshold referred to in point (b) of Article 3(2) of Directive 2011/61/EU, and where those managers are therefore subject to authorisation in accordance with Article 6 of that Directive, they may continue to use the designation ‘EuSEF’ in relation to the marketing of q...
- Target text: 2.   Without prejudice to the application of Article 46, only paragraphs 3 and 4 of this Article shall apply to the following AIFMs: (a) AIFMs which either directly or indirectly, through a company with which the AIFM is linked by common management or control, or by a substantive direct or indirect holding, manage portfolios of AIFs whose assets under management, including any assets acquired through use of leverage, in total do not exceed a threshold of EUR 100 million; or (b) AIFMs which either directly or indirectly, through a company with which the AIFM is linked by common management or co

## 090 [CROSS] `Articles 16 to 29`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0053` / `15`
- Target act/path: `32008R0765` / `20`
- Source context: ...Article 15(3) and Articles 16 to 29 of Regulation (EC) No 765/2008 shall apply to radio equipment. ...
- Target text: Article 20 Products presenting a serious risk 1.   Member States shall ensure that products which present a serious risk requiring rapid intervention, including a serious risk the effects of which are not immediate, are recalled, withdrawn or that their being made available on their market is prohibited, and that the Commission is informed without delay thereof, in accordance with Article 22. 2.   The decision whether or not a product represents a serious risk shall be based on an appropriate risk assessment which takes account of the nature of the hazard and the likelihood of its occurrence.

## 091 [CROSS] `Articles 26 to 35`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32015R0104` / `annex-zone.chunk 35`
- Target act/path: `32009R1224` / `33`
- Source context: ... the programme applies. CHAPTER IV Management 10.   General obligation Member States shall manage the maximum allowable effort in accordance with the conditions laid down in Article 8 of Regulation (EC) No 2166/2005 and Articles 26 to 35 of Regulation (EC) No 1224/2009. 11.   Management periods 11.1. A Member State may divide the days present within the area set out in Table I into management periods of durations of one or more calendar months. 11.2. Th...
- Target text: Article 33 Recording of catches and fishing effort 1.   Each flag Member State shall record all relevant data, in particular data referred to in Articles 14, 21, 23, 28 and 62, on fishing opportunities as referred to in this Chapter, expressed both in terms of landings and, where appropriate, fishing effort, and shall keep the originals of those data for a period of three years or longer in accordance with national rules. 2.   Without prejudice to specific rules laid down in Community legislation, before the 15th of each month, each flag Member State shall notify the Commission or the body des

## 092 [CROSS] `Article 25`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32019R1122` / `annex-zone.chunk 8`
- Target act/path: `32003L0087` / `25`
- Source context: ...the transferring and acquiring account was an ETS management account as indicated in Table I-I of Annex I. 5. On 1 May each year, the following information shall be published on agreements which are in force pursuant to Article 25 of Directive 2003/87/EC recorded by the EUTL by 30 April: (a) holdings of allowances issued in the linked emissions trading system on all accounts in the Union Registry; (b) number of allowances issued in the linked emi...
- Target text: Article 25 Links with other greenhouse gas emissions trading schemes 1.   Agreements should be concluded with third countries listed in Annex B to the Kyoto Protocol which have ratified the Protocol to provide for the mutual recognition of allowances between the Community scheme and other greenhouse gas emissions trading schemes in accordance with the rules set out in Article 300 of the Treaty. 2.   Where an agreement referred to in paragraph 1 has been concluded, the Commission shall draw up any necessary provisions relating to the mutual recognition of allowances under that agreement in acco

## 093 [CROSS] `Article 4(1)(61)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32017R1131` / `2.7`
- Target act/path: `32013R0575` / `4.1.61`
- Source context: ...(7) ‘securitisation’ means securitisation as defined in Article 4(1)(61) of Regulation (EU) No 575/2013; ...
- Target text: (61) ‧securitisation‧ means a transaction or scheme, whereby the credit risk associated with an exposure or pool of exposures is tranched, having both of the following characteristics: (a) payments in the transaction or scheme are dependent upon the performance of the exposure or pool of exposures; (b) the subordination of tranches determines the distribution of losses during the ongoing life of the transaction or scheme;

## 094 [CROSS] `Article 4(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32021R1059` / `176.20`
- Target act/path: `32021R1057` / `4.1`
- Source context: ...ves. However, the list of the specific objectives under the different policy objectives should be adapted to the specific needs of Interreg in order to allow for ESF-type interventions, according to points (a) to (l) of Article 4(1) of Regulation (EU) 2021/1057 of the European Parliament and of the Council (13) through joint actions under Interreg programmes. ...
- Target text: 1.   The ESF+ shall support the following specific objectives in the policy areas of employment and labour mobility, education, social inclusion, including contributing to poverty eradication, and thereby also contributing to the policy objective ‘a more social and inclusive Europe implementing the European Pillar of Social Rights’ referred to in Article 5, point (d), of Regulation (EU) 2021/1060: (a) improving access to employment and activation measures for all jobseekers, in particular young people, especially through the implementation of the Youth Guarantee, for long-term unemployed and d

## 095 [CROSS] `Article 99`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32013R0575` / `4.1.103`
- Target act/path: `32009L0138` / `99`
- Source context: ... items are classified in Tier 1 within the meaning of Directive 2009/138/EC in accordance with Article 94(1) of that Directive and the inclusion of those items is limited by the delegated acts adopted in accordance with Article 99 of that Directive; ...
- Target text: Article 99 Implementing measures The Commission shall adopt implementing measures laying down: (a) the quantitative limits referred to in Article 98(1) and (2); (b) the adjustments that should be made to reflect the lack of transferability of those own-fund items that can only be used to cover losses arising from a particular segment of liabilities or from particular risks (ring-fenced funds). Those measures, designed to amend non-essential elements of this Directive by supplementing it, shall be adopted in accordance with the regulatory procedure with scrutiny referred to in Article 301(3). S

## 096 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32014L0059` / `55.3`
- Target act/path: `32010R1093` / `14`
- Source context: ...bmit those draft regulatory technical standards to the Commission by 3 July 2015. Power is delegated to the Commission to adopt the regulatory technical standards referred to in the first subparagraph in accordance with Articles 10 to 14 of Regulation (EU) No 1093/2010. ...
- Target text: Article 14 Non-endorsement or amendment of draft regulatory technical standards 1.   In the event that the Commission does not endorse a draft regulatory technical standard or amends it as provided for in Article 10, the Commission shall inform the Authority, the European Parliament and the Council, stating its reasons. 2.   Where appropriate, the European Parliament or the Council may invite the responsible Commissioner, together with the Chairperson of the Authority, within 1 month of the notice referred to in paragraph 1, for an ad hoc meeting of the competent committee of the European Parl

## 097 [CROSS] `Article 14(1)`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32018L2001` / `15.7`
- Target act/path: `32012L0027` / `14.1`
- Source context: ...riate, include spatial analysis of areas suitable for low-ecological-risk deployment and the potential for small-scale household projects and shall be included in the second comprehensive assessment required pursuant to Article 14(1) of Directive 2012/27/EU for the first time by 31 December 2020 and in the subsequent updates of the comprehensive assessments. ...
- Target text: 1.   By 31 December 2015, Member States shall carry out and notify to the Commission a comprehensive assessment of the potential for the application of high-efficiency cogeneration and efficient district heating and cooling, containing the information set out in Annex VIII. If they have already carried out an equivalent assessment, they shall notify it to the Commission. The comprehensive assessment shall take full account of the analysis of the national potentials for high-efficiency cogeneration carried out under Directive 2004/8/EC. At the request of the Commission, the assessment shall be

## 098 [CROSS] `Article 8`
- Resolution: `exact`; keyword: `Article`
- Source act/path: `32014R0909` / `54.4.a`
- Target act/path: `32013L0036` / `8`
- Source context: ...(a) the separate legal entity is authorised as a credit institution as provided for in Article 8 of Directive 2013/36/EU; ...
- Target text: Article 8 Authorisation 1.   Member States shall require credit institutions to obtain authorisation before commencing their activities. Without prejudice to Articles 10 to 14, they shall lay down the requirements for such authorisation and notify EBA. 2.   EBA shall develop draft regulatory technical standards to specify: (a) the information to be provided to the competent authorities in the application for the authorisation of credit institutions, including the programme of operations provided for in Article 10; (b) the requirements applicable to shareholders and members with qualifying hold

## 099 [CROSS] `Articles 10 to 14`
- Resolution: `exact`; keyword: `Articles`
- Source act/path: `32020R1503` / `12.16.b`
- Target act/path: `32010R1095` / `10`
- Source context: ...ommission by 10 November 2021. Power is delegated to the Commission to supplement this Regulation by adopting the regulatory technical standards referred to in the first subparagraph of this paragraph in accordance with Articles 10 to 14 of Regulation (EU) No 1095/2010. ...
- Target text: Article 10 Regulatory technical standards 1.   Where the European Parliament and the Council delegate power to the Commission to adopt regulatory technical standards by means of delegated acts under Article 290 TFEU in order to ensure consistent harmonisation in the areas specifically set out in the legislative acts referred to in Article 1(2), the Authority may develop draft regulatory technical standards. The Authority shall submit its draft standards to the Commission for endorsement. Regulatory technical standards shall be technical, shall not imply strategic decisions or policy choices an
