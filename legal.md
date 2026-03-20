COMPLIANCE NOTE
PROPOSITION
The platform is a consumer-facing verification service that assists individuals and families in 
conducting pre-matrimonial due diligence. Upon receiving a service request with basic primary 
identifiers, the platform conducts comprehensive searches across open and unrestricted data 
repositories, such as court records, company registrations, property records, social media public 
profiles, and government databases. The deliverable is a structured, consolidated digital report. 
The service relies solely on the lawful aggregation of public records, ensuring a fully compliant 
operational model that operates independently of restricted databases or unregulated third-party 
data brokers.
APPLICABLE LAWS
1. The Digital Personal Data Protection (DPDP) Act, 2023 & DPDP Rules, 2025
2. The Information Technology (IT) Act, 2000
3. CERT-In Cyber Security Directions (No. 20(3)/2022-CERT-In)
4. The Companies Act, 2013 / Limited Liability Partnership (LLP) Act, 2008
5. The Indian Contract Act, 1872
6. The Consumer Protection Act, 2019
7. The Bharatiya Nyaya Sanhita (BNS), 2023 (Section 356) / Civil Defamation
8. Constitutional Torts (Right to Privacy) – Article 14
9. The Credit Information Companies (Regulation) Act, 2005 (CICRA)
10. Reserve Bank of India (RBI) Master Directions
11. United Kingdom: UK GDPR & Data Protection Act (DPA) 2018
12. United Arab Emirates: Federal Decree-Law No. 45 of 2021 (PDPL)
13. United States: California Consumer Privacy Act (CCPA / CPRA)
QUESTIONS
1. Since we are aggregating only publicly available data — eCourts, MCA21, property 
registrations, public social media — does the DPDP Act 2023 still apply to us, given that 
the subject of the report has not directly interacted with our platform?
Under Section 3(c)(ii) of the DPDPA, the Act does not apply to personal data made publicly 
available by:
1. The Data Principal (the individual) to whom the data relates; or
2. Any other person under a legal obligation to publish it.
Note: The Data Fiduciary must definitively verify who caused the publication. Implied consent is 
invalid. If it is ambiguous whether the individual published it (e.g., third-party posts) or if the data 
transitions from public to private, the exemption fails.
ANALYSIS
Data Source Category Exemption Status Legal Reasoning & Associated 
Risks
Statutory & Government 
Records (eCourts, MCA21, 
Property Registrations)
Exempt (DPDPA does 
not apply)
Satisfies Limb 2: Government 
registries are under a statutory "legal 
obligation" to maintain and publish 
these records. No consent or notice 
is required.
Public Social Media Profiles Highly Vulnerable
(DPDPA likely applies -
unclear as this has not
been interpreted by a 
court or clarified by the 
legislature yet)
Could Fail Limb 1: Platform must 
prove the individual explicitly 
"caused" the publication. 
• Automated tools cannot 
distinguish if a post was self￾published, posted by a news outlet, 
or tagged by a friend.
• A profile public during scraping 
might become private later, making 
continued processing legally murky.
CONCLUSION
The DPDPA does not apply to the aggregation of government and statutory records. However, it 
likely applies to the indiscriminate aggregation of public social media data (the same has not been 
clarified yet by courts or the legislature), as the platform cannot reliably verify that the Data 
Principal explicitly caused the publication of every data point. Relying on a blanket "publicly 
available" defense is risky.
2. Does aggregating multiple pieces of individually public information into a single 
compiled report create any additional legal obligation that wouldn’t exist if each piece 
were accessed separately?
RULE
• The DPDP Act, 2023: Section 3(c)(ii) provides an absolute exemption for publicly 
available data. The Act contains no provision that penalizes the profiling or aggregation of 
this exempt data.
• The IT Act, 2000: Section 43 imposes strict civil liability against anyone who accesses a 
computer network or extracts a "computer data base" without permission from the network 
owner.
ANALYSIS
The legal risk of data aggregation bifurcates entirely depending on which statute is applied:
Relevant Acts Impact of Aggregating Data
DPDP Act Because the raw data points are categorically exempt, compiling them 
into a PDF does not retroactively extinguish the privacy exemption.
IT Act Manual access has implied permission, but deploying automated 
scrapers to aggregate thousands of records inherently requires 
bypassing technical and contractual barriers which could violate 
section 43 of the IT A.
Bypassing Barriers & ToS: To aggregate data at scale, platforms typically must bypass technical 
controls or violate contractual rules, which instantly revokes the "permission" required under 
Section 43 of the IT Act:
• Bypassing Technical Measures: Much like the Computer Fraud and Abuse Act (CFAA) 
in the US or the Computer Misuse Act in the UK, Indian cyber law treats bypassing 
CAPTCHA challenges, IP blocks, or login requirements as unauthorized access. Bypassing 
these technical barriers could constitute a Section 43 violation, regardless of whether the 
underlying data is public.
• Violating Terms of Service (ToS): Major platforms expressly revoke permission for 
automated data collection in their ToS. Violating these clauses constitutes extracting a 
database "without permission" under Indian law. For example:
o Instagram: Explicitly prohibits collecting information in an automated way without 
express permission, even if logged into an account.
o LinkedIn: Prohibits the use of software, scripts, robots, or crawlers to scrape their 
services or copy profiles.
o Facebook: States users "will not engage in Automated Data Collection without 
Facebook’s express written permission."
CONCLUSION
Aggregating publicly available data does not create new privacy obligations under the DPDP Act. 
However, the method of aggregation creates severe liabilities under Section 43 of the IT Act. 
Bypassing CAPTCHAs or violating platform ToS via automated scrapers constitutes unauthorized 
extraction, making the platform liable for compensatory damages.
3. The person ordering the report is giving us consent to process data for matrimonial 
verification purposes. However, the subject of the report is not giving consent. Is this a 
legal problem under DPDP 2023 or any other Indian law?
RULE
• DPDP Act, 2023: (Sections 2(j) & 6(1)): Only the specific person the data is about (the 
"Data Principal") can give valid consent. You cannot legally consent on behalf of another 
competent adult.
o The Public Data Exemption (Section 3(c)(ii)): If the data is strictly publicly 
available (e.g., government records or public posts), the Act does not apply.
• IT Act, 2000: (Section 43(b)): One must have permission from the website owner (like the 
government or LinkedIn) to download, copy, or extract a computer database from their 
servers.
ANALYSIS
The legal reality of relying on a customer's "proxy consent" breaks down depending on the type of 
data and how you extract it:
Scenario Legal Risk
Using Public Data (eCourts, 
MCA records)
No Privacy Risk. Because publicly available data falls under the
Sec 3(c)(ii) exception, the subject's consent is not relevant or 
required anyway.
Using Private Data (Leaked 
info, private posts)
DPDP Violation. Processing private data without the subject's
direct consent violates Sec 6(1).
Scraping Websites
(Automated extraction)
IT Act Violation. Extracting a database without the host server's 
permission violates Sec 43(b), regardless of any customer 
agreement.
CONCLUSION
Under the DPDP Act, only the actual Data Principal can give consent. However, because your 
platform relies on publicly available data which falls entirely under the statutory exemption, the 
lack of the subject's consent is not relevant anyway. That said, a customer's consent can never 
protect your platform from cyber trespass laws (Section 43(b) of the IT Act) if unauthorized web 
scrapers are used to get that data.
4. Are there any specific categories of data — financial history, social media opinions, 
religious views, past relationships — that we are legally prohibited from including in 
such a report regardless of their public availability?
RULE
• The DPDP Act, 2023: The legislation completely abandons the older concept of "Sensitive 
Personal Data or Information" (SPDI), treating all personal data uniformly. More 
importantly, because the platform processes strictly publicly available data, the DPDP Act 
does not apply to the business at all due to the absolute exemption under Section 3(c)(ii). 
Even if the Act did apply, there is no statutory classification that restricts specific data 
categories.
• The IT Act, 2000: Sections 66E, 67, and 67A strictly prohibit the capturing, publishing, 
or transmitting of images of private bodily areas, obscene material, or sexually explicit acts 
in electronic form.
• RBI Regulations (CICRA, 2005): The Credit Information Companies (Regulation) Act 
restricts the compilation and commercial sharing of raw credit data and loan defaults 
exclusively to RBI-licensed credit bureaus.
ANALYSIS
The legal liability of including specific data categories depends entirely on distinguishing between 
objective public records, regulated financial data, and subjective content:
• Financial History: Compiling objective relationship history (such as a public divorce 
decree from eCourts) is permissible. However, the platform is strictly prohibited from 
including raw financial loan defaults. Scraping and selling "Wilful Defaulter" lists 
published by banks violates RBI regulations, as the business cannot legally operate as an 
unlicensed credit bureau. Financial records must be strictly limited to public court litigation 
(e.g., a cheque bounce case under the Negotiable Instruments Act), not raw banking default 
data.
• Subjective Opinions and Religious Views: The platform must strictly exclude a subject's 
subjective opinions, political statements, or religious views scraped from social media. If 
a report highlights an aggressive religious or political post, it ceases to be mere data 
aggregation and becomes a subjective character assessment. This exposes the business to 
substantial civil and criminal defamation lawsuits. To neutralize this risk, the report's fields 
must be restricted strictly to objective, binary data (e.g., "Company Director Status: 
Active" or "Litigation History: 2 pending civil suits").
• Intimate or Obscene Data: If an intimate photograph is leaked online, it is technically 
"publicly available." However, aggregating and transmitting this data in a commercial 
report constitutes a direct criminal offense under the IT Act (Sections 66E and 67). The 
DPDP Act's public data exemption provides no immunity against criminal prosecution for 
distributing obscenity. Consequently, the platform must extract only text and enforce a 
strict prohibition against downloading or embedding photographs or visual media to 
eliminate bodily privacy and copyright risks.
CONCLUSION
While the DPDP Act does not apply to the platform's public data and contains no "sensitive" 
classifications but regardless other statutes heavily restrict publishable content. RBI regulations 
explicitly prohibit the aggregation of bank loan defaults. The IT Act criminalizes the distribution 
of obscene or leaked intimate material. Finally, including subjective social media opinions or 
religious views exposes the business to severe defamation liabilities, necessitating a strict 
operational adherence to objective, text-based public records.
5. Does our service fall under the definition of a “private detective agency” under the 
Private Security Agencies Regulation Act 2005? If yes, do we need a license to operate 
in Delhi and other states?
RULE
• Private Security Agencies Regulation, 2005: This law strictly regulates businesses that 
provide physical security services (like deploying armed guards or bouncers to protect 
property or people). It does not mention or regulate digital data aggregators or tech 
platforms.
• Private Detective Agencies Bill, 2007: The government tried to create a law to regulate 
private investigators and background check agencies. However, this bill was officially 
withdrawn in Parliament in March 2020.
ANALYSIS
Law Applicability
PSARA (Security License) Not Applicable. PSARA forces security 
agencies to run background checks on their
own guards but providing background checks 
as a digital service to others does not make you 
a security agency.
Private Detective License The license doesn't exist as the 2007 Bill was 
never passed, India currently has no central or 
state law that requires a license to be a private 
detective or run a digital background check 
firm.
CONCLUSION
The service does not fall under PSARA. Furthermore, because there is currently no active law 
regulating private detectives in India, the platform does not need a specialized "Private Detective 
License" or "PSARA License" to operate anywhere in the country.
6. Should we register as a Private Limited Company from day one, and does the nature of 
this business create any specific liability concerns that would make a different structure 
preferable?
RULE
• The Companies Act, 2013: Section 9 establishes the company as a "body corporate," 
meaning it has a legal identity completely separate from its founders. Section 2(22) ensures 
that in a company limited by shares, the founders' financial liability is strictly limited to the 
amount they invested in their shares.
• The Limited Liability Partnership (LLP) Act, 2008: Section 3 declares an LLP to be a 
body corporate and a separate legal entity from its partners. Sections 27 and 28 explicitly 
state that partners are not personally liable for the business's debts or obligations just by 
being partners.
• The Information Technology (IT) Act, 2000 (Section 85): If a company commits a cyber 
offense (like unauthorized web scraping), the directors/partners can be held personally
liable and punished, unless they prove they exercised "due diligence" to prevent it.
ANALYSIS
Among the most popular business structures, Private Limited Companies (Pvt Ltd) and Limited 
Liability Partnerships (LLP) stand out as preferred choices for most new businesses. Both offer 
limited liability protection but there are some key differences that may make one of them more 
favorable for the business model. 
Feature Private Limited 
Company (Pvt. Ltd.)
Limited Liability 
Partnership (LLP)
Relevance to the 
Matrimonial Startup
Funding & 
Investment
Can issue equity shares. 
Highly attractive to 
Venture Capital (VC) 
and Angel Investors.
Cannot issue shares. 
Funding is strictly limited 
to partner contributions or 
bank debt.
If the founders plan to raise 
tech capital to build the API 
infrastructure, they should
be a Pvt. Ltd.
Employee 
Incentives
Can issue ESOPs 
(Employee Stock 
Options).
Cannot issue ESOPs. Pvt. Ltd stands out here as 
ESOPs are crucial for 
attracting top-tier talent to 
setup the company.
Compliance 
& Cost
High. Mandatory board 
meetings, statutory 
audits (regardless of 
turnover), and complex 
annual filings.
Low. No mandatory board 
meetings. Audits are only 
required if turnover 
exceeds ₹40 lakh.
LLP preferrable. Better for a 
self-funded, smaller lifestyle 
business to keep initial costs 
low.
B2B 
Credibility
High credibility. 
Preferred by large 
corporations and API 
partners.
Perceived as a professional 
service (consulting, 
accounting etc.) or small 
business structure.
Pvt. Ltd makes more sense 
here as credibility is 
important if pivoting to sell 
B2B API access to 
matrimonial websites like 
Shaadi.com.
Note:
- Because the platform aggregates public data that might be outdated, the risk of a subject filing a 
massive civil defamation suit (e.g., claiming a false report ruined their marriage) is high. If you 
are under a limited liability structure, the company takes the hit for these types of lawsuits. The 
financial loss stops at the company's bank account, keeping the founders' personal money 
completely safe.
- While the corporate veil protects against defamation, it does not protect against cyber crimes. If 
the platform's engineers deploy illegal scrapers that bypass government CAPTCHAs, Section 85 
allows the government to pierce the veil and hold the founders/directors personally liable for the 
cyber trespass.
- If you start out as an LLP to keep costs low, the law (Section 366 of the Companies Act, 2013) 
allows you to officially upgrade to a Pvt. Ltd. later on. However, this requires unanimous partner 
consent, creditor clearances (NOCs), and public newspaper announcements.
CONCLUSION
A Private Limited Company is the strongly preferred structure if they intend to raise capital, issue 
ESOPs to engineers, and scale into a B2B API provider. However, if due to the compliance and 
costs of a Pvt Ltd., an LLP structure is preferred, the structure can be changed thereafter. 
7. Are there any RBI regulations we need to be aware of if we eventually want to include 
financial background data such as publicly available loan default records or court 
judgments related to financial disputes?
RULES
• Credit Data Monopoly (CICRA, 2005 - Sec 3): Only entities holding a formal RBI 
Certificate of Registration can carry on the "business of credit information." Currently, 
only 4 entities (CIBIL, Experian, Equifax, CRIF) are licensed Credit Information 
Companies (CICs).
• Definition of Credit Info (Sec 2(d)): Broadly covers loan amounts, security nature, credit 
history, and borrower defaults.
• "Specified User" Limit (Sec 2(l)): Regulated credit data can only be shared with 
authorized entities (banks, NBFCs) for permissible legal purposes (like loan assessments).
• DPDP Act Exemption (Sec 3(c)(ii)): Personal data legally required to be public (like 
eCourts data) is exempt from privacy restrictions.
• RBI Master Directions (July 2024): The RBI explicitly mandates that all regulated 
entities must submit their lists of large defaulters (₹1 crore and above) and wilful defaulters 
(₹25 lakh and above) directly to CICs. The law designates these CICs as the sole entities 
responsible for displaying this default data on their websites.
ANALYSIS
The Business’ liability depends on where you get the data:
Data Source Legal Explanation
Aggregating Loan 
Defaults (e.g., 
Bank lists)
Under the 2024 RBI Master Directions, publishing defaulter data is 
strictly the domain of registered CICs. Scraping these lists to sell in a 
commercial report makes you an unregistered credit bureau, directly 
violating Section 3 of CICRA. Furthermore, families are not "Specified 
Users," and matchmaking is not a legal reason to access regulated credit 
histories.
Aggregating 
Court Judgments
(e.g., eCourts)
Extracting a public record of a financial dispute (e.g., a cheque bounce 
under Section 138 of the Negotiable Instruments Act) is totally different. 
This is public litigation history, not a raw credit report. It falls outside RBI 
jurisdiction and is shielded by the DPDP Act’s public data exemption.
CONCLUSION
Yes, there are severe RBI regulations. If the platform scrapes and sells actual loan default lists 
(which are tightly regulated by the new 2024 RBI directives), it is illegally operating as an 
unregistered Credit Information Company. However, compiling public court judgments regarding 
financial disputes is completely legal; it is an aggregation of public litigation history, not a 
regulated credit report, and avoids RBI penalties entirely.
8. What specific disclaimers must our reports and terms of service contain to protect us 
from liability if a report is incomplete, contains an error, or leads to a broken 
engagement or damaged reputation?
RULE
• The Indian Contract Act, 1872: A business is legally allowed to limit its liability through 
contracts (like Terms of Service), provided the terms are not unlawful, fraudulent, or 
against public policy (Section 23).
• Consumer Protection Act, 2019: Protects paying customers from "deficiency in service." 
Additionally, Section 2(46) defines an "unfair contract" as one that causes a significant 
change or imbalance in the rights of the consumer. Consumer courts have the power to 
declare unfair contract terms null and void.
ANALYSIS
Because the platform pulls data from government databases (like eCourts) that are inherently prone 
to delays and clerical errors, the business assumes massive legal risk the moment it sells a report. 
If the automated system misses a recent court acquittal and falsely labels a subject as a criminal, 
the subject could sue the platform for defamation (e.g., for ruining a marriage), and the customer 
could sue for a faulty product or deficiency in service.
To survive this, the business must actively shift the legal risk onto the customer using strict, well￾drafted disclaimers in its Terms of Service and on the cover page of every PDF report. The platform 
must embed the following protections:
• The "As-Is" Disclaimer: Clearly state that the report is an automated snapshot of public 
records at a specific timestamp, provided "as-is" without any warranties regarding accuracy 
or completeness.
• No Professional Verification: Clarify that the platform does not independently verify the 
factual truth of the government records and that the report does not constitute a certified 
private investigation or professional advice.
• Waiver & Liability Cap: Force the user to agree that the business is not liable for indirect 
or consequential damages (like emotional distress or canceled wedding costs). The 
maximum legal liability must be strictly capped to the nominal fee the customer paid for 
the report.
• Customer Indemnity: Require the user to legally indemnify and hold the platform 
harmless from lawsuits if the user misuses, publishes, or illegally distributes the report.
Note on Disclaimer Validity: While disclaimers are essential, a business cannot blindly rely on 
blanket liability waivers. Under Section 23 of the Indian Contract Act, a disclaimer is void per se 
if it defeats the law or is opposed to public policy. More importantly, under Section 2(46) of the 
Consumer Protection Act, 2019, if a liability waiver is so extreme that it imposes an unreasonable 
condition putting the consumer at a severe disadvantage, a court can classify it as an "unfair 
contract" and strike it down. Therefore, the disclaimers must be drafted to be clear, reasonable, 
and proportionate to the service provided.
CONCLUSION
Because the platform acts as a publisher of data that can be outdated or flawed, the business is 
strictly liable for the real-world fallout of the reports it sells. To protect the company, it must 
embed comprehensive "As-Is" warranties and strict liability caps into its contracts. However, these 
disclaimers must be reasonably balanced to ensure they are not struck down as "unfair contracts" 
under Indian consumer protection laws.
9. If a subject of one of our reports finds out they were investigated and claims defamation 
or privacy violation, what is our legal exposure? Does it matter whether the information 
in the report was accurate or not?
RULE
• Privacy: The DPDP Act, 2023 (Section 3(c)(ii)) provides an absolute exemption for 
personal data made publicly available by legal obligation.
• Criminal Defamation: Section 356 of the Bharatiya Nyaya Sanhita (BNS) penalizes the 
publication of reputation-harming imputations.
o Exception 1: Protects "truth published for the public good." However, the statute 
explicitly states that whether an act is for the "public good" is a subjective question 
of fact determined by a judge.
o Exception 4: Protects the "publication of reports of proceedings of courts," offering 
a more objective legal shield.
• Civil Defamation: Under common law, defamation requires a false statement that lowers 
a person's reputation. "Truth" serves as an absolute defense.
ANALYSIS
1. Exposure to Privacy Violations: If the platform strictly quarantines its data extraction to 
statutory public records (like eCourts or MCA), privacy claims will fail prima facie. The absolute 
exemption under Section 3(c)(ii) of the DPDP Act applies because the government mandates the 
publication of these records. A subject cannot successfully sue for a privacy violation over a 
document the government legally requires to be public. However, scraping non-exempt data (e.g., 
private social media posts) introduces massive exposure, risking DPDP Board investigations and 
severe financial penalties.
2. Exposure to Defamation (The Accuracy Factor): Factual accuracy is the absolute crux of the 
platform's tort exposure.
• If the Report is 100% Accurate: Civil defamation claims fail immediately, as truth is an 
absolute defense in tort law. Criminal defamation under BNS Section 356 is more complex; 
relying on Exception 1 is a weak strategy because convincing a court that a private 
matrimonial background check serves the "public good" is highly debatable. However, 
accurately reproducing a public court judgment is strictly protected under Exception 4.
• If the Report is Inaccurate: This is a severe liability scenario. Public data frequently suffers 
from clerical errors or delayed updates. If the platform scrapes a pending criminal FIR but 
misses a subsequent High Court order quashing it, the business has published a materially 
false, defamatory statement. If this falsehood leads to a broken engagement, the platform 
cannot rely on the "public records" defense and exposes itself to massive compensatory 
damages for loss of reputation.
CONCLUSION
The platform's exposure to privacy violations is effectively neutralized if it restricts its operations 
entirely to statutory public records. Conversely, exposure to defamation hinges entirely on factual 
accuracy. While an accurate report provides a robust defense against civil and criminal defamation, 
publishing an inaccurate or outdated report strips away these legal shields, exposing the business 
to crippling tort liability for damages.
10. Can someone file a case against us under the IT Act 2000 or any other law for 
aggregating and selling a report about them even if all data used was publicly available?
RULE
• The IT Act, 2000 (Section 43): Penalizes unauthorized extraction of a "computer data 
base." The aggrieved party is the owner of the computer resource, not necessarily the 
subject of the data.
• The DPDP Act, 2023: Section 3(c)(ii): Exempts personal data made publicly available by 
legal obligation or the user.
o Section 27 & 29: Grants the Data Principal the right to register a grievance and file 
formal complaints with the Data Protection Board (DPB) for unlawful processing.
• Constitutional & Tort Law (Right to Privacy):
o Article 21 (K.S. Puttaswamy v. Union of India): Recognizes privacy as a 
fundamental right.
o R. Rajagopal vs State of T.N. (1994): The Supreme Court held that while 
individuals have a "right to be let alone," this right is significantly limited if the 
information is already a matter of public record.
• Defamation (BNS Section 356 & Civil Tort): Publishing false information that lowers a 
person's moral or intellectual character is defamation. Truth and "public good" are the 
primary legal defenses.
ANALYSIS
While the data may be public, commercializing aggregated profiles opens the platform to several 
specific avenues of litigation from the subject:
Applicable Law Explanation
IT Act (Sec 43) The subject cannot sue the platform directly unless their
personal server was scraped. Only the database owner 
(e.g., the Government or LinkedIn) can sue for 
unauthorized extraction.
DPDP Act (Sec 27 & 29) The subject can trigger a DPB investigation. The burden 
shifts to the platform to prove every data point falls 
under the Sec 3(c)(ii) exemption. One non-exempt point 
(e.g., a scraped blog) risks massive financial penalties.
Privacy: Tort Law & Art. 21 The subject can seek an injunction, arguing commercial 
profiling violates residual privacy. However, the 
platform can strongly defend itself using the R. 
Rajagopal precedent, arguing the data is strictly public 
record.
Defamation: BNS Sec 356 & Civil 
Law
This is the biggest financial trap. If the platform scrapes 
a pending FIR but misses the subsequent acquittal, the 
report is materially false. If this ruins a wedding, the 
subject can sue for massive compensatory damages.
CONCLUSION
Yes, the data subject can absolutely file a case. While they generally lack the legal standing to sue 
for cyber trespass under the IT Act, they possess formidable legal weapons. They can trigger DPDP 
Board investigations to challenge the "publicly available" exemption, file civil suits for invasion 
of privacy, and initiate high-stakes defamation litigation if the compiled public records are 
outdated or misrepresented.
11. Under DPDP 2023, how long are we legally permitted or required to retain the data we 
collect for a report? What is our obligation to delete it after delivery?
RULE
The Digital Personal Data Protection (DPDP) Act, 2023, contains a specific exemption for public 
information. Under Section 3(c)(ii), the law explicitly states: "The provisions of this Act shall not 
apply to... personal data that is made or caused to be made publicly available by the Data 
Principal... or any other person who is under an obligation under any law."
When the statute says the provisions "shall not apply," it means the entire framework of the law
including the strict rules that force businesses to delete data or maintain retention logs is 
completely bypassed.
ANALYSIS
Since the platform is built entirely on using publicly available data, the standard privacy rules are 
not applicable to the business. Because we are not acting as a regulated "Data Fiduciary" for this 
specific information, we have no statutory mandate to erase it. Legally speaking, we could keep 
these public records indefinitely.
However, operating without these rules creates a massive "contamination risk." The legal 
exemption applies on a data-point by data-point basis, not to the database as a whole. If thousands 
of reports are stored forever, the chance of accidental contamination is incredibly high. If just one 
piece of non-public data (such as a private social media post or a leaked document) sneaks into the
servers, the public data shield collapses for that specific information. Thus keeping the private data 
indefinitely would not be wise and staying complaint with the DPDP Act would still be prudent.
DPDP ACT DATA RETENTION RULES (FOR REGULATED DATA)
If any data falls outside the public exemption (or regarding the billing and account data of paying 
customers), the business must strictly follow the data erasure mandates outlined in Section 8(7) of 
the DPDP Act. The statutory obligations are as follows:
• A Data Fiduciary must permanently delete personal data as soon as it is reasonable to 
assume that the specific purpose for which it was collected has been fulfilled (e.g., once 
the background check is delivered and the commercial transaction is complete).
• The data must be erased immediately if the Data Principal actively withdraws their consent.
• Retention of the data past the aforementioned triggers is only permitted if compliance with 
another valid Indian law legally mandates it (such as retaining financial invoices for tax 
compliance or maintaining server logs to satisfy CERT-In cybersecurity directions).
• If the personal data was shared with any external vendors or technology providers (Data 
Processors), the Data Fiduciary is legally obligated to ensure that those processors also 
erase the data from their respective systems.
CONCLUSION
Since the business is only using publicly available data, the DPDP Act's strict retention and 
deletion rules do not apply. However, because there is a high chance of data contamination ruining 
this legal protection, there should be compliance with DPDP standards regardless.
12. If we experience a data breach and reports are leaked — exposing sensitive personal 
information about subjects — what is our legal liability and what notifications are we 
required to make?
RULES
• The Cyber Law (CERT-In & IT Act Sec 70B): The Indian Computer Emergency 
Response Team (CERT-In) is the cybersecurity watchdog. Their rules mandate that 
businesses report cyber incidents (like data leaks or unauthorized access) within a 6-hour
window of noticing them.
o Pre-Breach Rules: Before a breach even happens, CERT-In forces businesses to 
synchronize all server clocks to the government's official time (NIC/NPL), keep 
system traffic logs for 180 days in India, and designate an official Point of Contact.
o Penalties: Failing to report to CERT-In or follow these rules can lead to up to 1 
year in prison or fines under Sec 70B.
• The Privacy Law (DPDP Act 2023 & Rules 2025): Section 8 forces businesses to notify 
the Data Protection Board (DPB) and the affected individuals. The 2025 Rules say the DPB 
must be notified within 72 hours.
o Penalties: Failing to notify the DPB or the affected subjects can result in fines of 
up to ₹250 crore under Section 33.
ANALYSIS
There are a lot of overlapping timelines because of the various acts governing this scenario: 
• The moment you detect hackers stealing reports, the first clock starts. You have exactly 6 
hours to submit a technical report to CERT-In as per the rules. 
• Within 72 hours, you must file a detailed report with the Data Protection Board explaining 
how the breach happened, how many people are affected, and how you are fixing it.
• You must email the people whose reports were leaked in plain, simple English. You have 
to tell them exactly what was stolen and how they can protect themselves from identity 
theft.
• If CERT-In investigates the breach and finds the server clocks weren't synced to the 
government's time servers, or you didn't keep the system logs for 180 days, the business
will be penalized for breaking their technical rules, increasing your liability.
• If the stolen reports were heavily encrypted and the hackers couldn't actually read them 
(because you kept the decryption keys safe), you might be legally exempt from having to 
notify the victims, though you still have to tell the government.
CONCLUSION
The legal liability for a leaked report is catastrophic, reaching up to ₹250 crore in fines plus 
potential jail time for directors. You are legally required to execute a coordinated, high-stress 
notification plan: a technical report to CERT-In within 6 hours, a regulatory report to the DPB 
within 72 hours, and a plain-language warning to the affected subjects.
13. Are we required to appoint a Data Protection Officer given the nature of our business, 
or does that obligation only kick in at a certain scale?
RULES
• The DPO Threshold (Section 10, DPDP Act): The statutory obligation to appoint a 
formal, India-based Data Protection Officer applies exclusively to organizations notified 
by the Central Government as a "Significant Data Fiduciary" (SDF).
• SDF Criteria: The government assesses SDF status based on:
1. Volume and sensitivity of personal data processed.
2. Risk of harm to Data Principals.
3. Potential impact on the sovereignty, security, or electoral democracy of India.
• Standard Fiduciaries (DPDP Rules, 2025): Organizations not notified as SDFs are 
"Standard Data Fiduciaries." They do not need a DPO. They only must publish the contact 
details of a designated person to answer questions and handle grievances.
• The Exemption Clause (Section 3(c)(ii)): Data made publicly available by legal mandate 
or by the user does not fall under the Act's regulatory purview.
ANALYSIS
Applying these rules to the background verification platform reveals that the DPO requirement 
does not trigger for its current operational model:
Fiduciary 
Classification
Legal Criteria Platform's Current Status Resulting Obligation
Significant 
Data Fiduciary 
(SDF)
Massive data 
volume, high 
sensitivity, 
systemic public 
risk (Sec 10).
Does Not Meet Criteria.
The platform is a standard 
B2C service. Furthermore, 
scraped public records 
(eCourts, MCA) are exempt 
(Sec 3) and likely won't 
count toward SDF volume 
metrics.
No DPO Required. The 
platform escapes heavy 
SDF burdens like 
mandatory DPIAs, 
independent audits, and 
hiring a formal DPO.
Standard Data 
Fiduciary
Any entity 
determining the 
purpose/means of 
processing 
personal data not 
classified as an 
SDF.
Meets Criteria. The 
platform processes the 
personal and payment data 
of its paying customers (the 
users searching the 
platform).
Grievance Contact 
Required. Must provide 
a mechanism for 
customers to exercise 
rights (e.g., account 
deletion) under DPDP 
Rules 2025.
CONCLUSION
No, the platform is not required to appoint a Data Protection Officer (DPO). Under the DPDP Act, 
2023, the DPO mandate strictly applies only if the government formally notifies the business as a 
Significant Data Fiduciary (SDF). For a standard startup processing basic customer billing and 
exempt public records, a formal DPO is legally unnecessary.
14. If we eventually want to sell API access to matrimonial platforms so they can offer our 
verification as a feature within their product, does that change our legal obligations in 
any way — particularly around consent and data sharing?
RULE
• The DPDP Act, 2023:
o Section 2: Distinguishes a "Data Fiduciary" (determines purpose/means of 
processing) from a "Data Processor" (processes data on behalf of the Fiduciary).
o Section 6: The obligation to obtain clear consent rests exclusively on the Data 
Fiduciary.
o Section 8(2): A Fiduciary must use a valid contract (Data Processing Agreement) 
to engage a Processor.
ANALYSIS
Pivoting to an API provider fundamentally rewires the platform's regulatory exposure, trading 
direct consumer privacy burdens for complex B2B contractual and cybersecurity risks:
Legal Issue Applicable Law Impact on Business 
Role 
Reclassification
DPDP Act (Sec 2 & 
6)
The matrimonial site becomes the Data Fiduciary. 
You become the Data Processor, legally eliminating 
your need to obtain user consent or handle privacy 
grievances.
Consent 
Verification
DPDP Act (Sec 8(2)) Since you no longer interact with users, you risk 
facilitating unlawful processing. You must enforce a 
strict Data Processing Agreement (DPA) forcing the 
client to guarantee they obtained user consent.
CONCLUSION
Selling API access radically changes the platform's legal obligations. It safely reclassifies the 
business as a Data Processor, effectively eliminating the requirement to obtain direct consumer 
consent under the DPDP Act. However, this shift requires the platform to heavily regulate its third￾party clients through strict contracts and technical safeguards to prevent downstream API abuse 
from triggering severe cyber-trespass liabilities under the IT Act.
15. For Indian diaspora customers ordering reports from outside India — UK, US, UAE —
on individuals living in India, does Indian law apply to us, to them, or both? Are there 
cross-border data transfer restrictions we need to navigate?
RULE
• Indian Law (DPDP Act, 2023): Governs data processing in India. It allows data to be sent 
to any country unless the government explicitly bans it (the "Negative List"). It also 
completely exempts public data (Section 3(c)(ii)).
• UK Law (UK GDPR & DPA 2018): Applies to any business worldwide if they actively 
"offer goods or services" to people located in the UK (Article 3). The Data Protection Act 
(DPA) 2018 supplements the UK GDPR, meaning if the GDPR applies, the strict domestic 
rules and penalties of the DPA 2018 also apply.
• UAE Law (PDPL, 2021): Applies to any entity worldwide that processes the data of 
people residing in the UAE (Article 2).
• US Law (California CCPA): The US does not have a consolidated data protection act
with each state having its own laws (some of which are not codified into an act). The 
California CCPA is the most comprehensive data protection act in the country and applies 
if a business targets California residents and hits certain size thresholds (e.g., processing 
the data of 100,000+ consumers).
ANALYSIS
To understand the liability of the Business, we have to look at the two different people involved:
Whose Data is it? Applicability of Foreign Laws
The Subject (The person in India being 
investigated)
Foreign laws do not protect people living in 
India. Under Indian law, because you are 
scraping strictly public records, the data is 
entirely exempt. You can freely email this 
report to the foreign customer because India 
hasn't banned data transfers to the US, UK, or 
UAE.
The Customer (The NRI paying for the report) If you actively target customers in London or 
Dubai, their local privacy laws govern how 
you handle their account, search history, and 
credit card data. For a UK customer, you are 
hit with a double burden: complying with both 
the UK GDPR and the strict domestic rules of 
the DPA 2018, exposing you to their 
regulators.
CONCLUSION
Both jurisdictions apply, but to different people. Indian law applies to the subject being 
investigated (shielding you because the data is public). However, if you actively target foreign 
residents to sell these reports, it triggers the strict extraterritorial jurisdiction of foreign laws (UK 
GDPR/DPA 2018, UAE PDPL, or US CCPA) governing how you must handle the paying 
customer's personal and billing data.
POSSIBLE SAFEGUARDS
1. Data Extraction & Technology Architecture
• Restrict automated extraction strictly to government registries (like MCA21 and eCourts) 
to ensure the business remains entirely within the public data exemption.
• Purchase official commercial API access or use licensed B2B data vendors instead of 
deploying unauthorized web scrapers to bypass CAPTCHAs, which triggers cyber trespass 
liability.
• Use human analysts for social media to ensure the subject self-published the data and to 
comply with website Terms of Service that ban automated bots.
• Extract text only and strictly prohibit the downloading of photos or videos to eliminate 
bodily privacy risks, while also excluding news articles or gossip blogs.
• Query government databases live for every single request instead of caching, storing, or 
reselling old reports, ensuring the platform never sells outdated (and therefore defamatory) 
case statuses.
2. Content Moderation & Terminology
• Strictly ban the inclusion of subjective social media opinions, religious views, or political 
commentary to neutralize defamation risks.
• Frame financial red flags exclusively as "Public Litigation Records" and never use 
regulated terms like "Credit History," "Loan Defaults," or aggregate bank defaulter lists.
• Present only raw, objective court data without using algorithms or AI to assign a "Financial 
Trust Score" or "Red Flag Rating."
• Brand the business legally as a "Data Aggregation Platform" and aggressively avoid terms 
like "Private Detective" or "Investigator" to prevent unnecessary police scrutiny.
3. Corporate Governance & Cybersecurity
• Register as a Private Limited Company (Pvt. Ltd.) from Day 1 to shield founders' personal 
assets and facilitate future funding.
• Obtain Directors and Officers (D&O) liability insurance immediately to cover potential 
legal defense costs.
• Document explicit board instructions forbidding illegal scraping to build a due diligence 
paper trail that protects founders from personal liability under Indian cyber law.
• Sync all servers to the government's official NIC/NPL time servers, keep backend traffic 
logs for 180 days within India, and draft a 6-hour Incident Response Plan to comply with 
CERT-In data breach rules.
• Encrypt all generated reports at rest and permanently delete them 30 days after delivery to 
minimize hack value and data contamination risks.
4. Contracts, Disclaimers, & User Rights
• Prominently state on every report that it is an automated snapshot of public registries at a 
specific timestamp, provided "as-is," without independent professional verification.
• Cap the platform's maximum liability strictly to the fee paid for the report, and require the 
customer to legally indemnify the business if they misuse or distribute the report.
• Redraft consent forms to make it clear the customer is only consenting to the processing of 
their own billing and account data, not granting proxy consent for the subject.
• Designate a grievance contact person and build a portal for subjects to dispute and rectify 
inaccurate profiles internally, while deliberately avoiding the statutory "Data Protection 
Officer" title to prevent unwanted regulatory attention.
• Accept payments only in INR (₹), use geo-neutral marketing, and ensure the Terms of 
Service dictate that Indian courts have exclusive jurisdiction to protect against foreign 
regulators.
• Enforce strict Data Processing Agreements with corporate clients (if pivoting to B2B API 
access) requiring them to obtain user consent, paired with data erasure mandates and 
aggressive API rate-limiting to prevent server abuse.