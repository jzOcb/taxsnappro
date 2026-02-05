# Legal Compliance Review — ai-tax Documentation

**Review Date:** February 5, 2026
**Reviewed By:** AI Legal Review Agent (pre-attorney review)
**Status:** DRAFT — For attorney review before finalization
**Classification:** Confidential — Attorney Work Product Preparation

---

## Executive Summary

Four legal compliance documents were reviewed for the ai-tax AI-powered tax preparation SaaS product. The documents demonstrate strong foundational work — particularly the WISP, which is among the most thorough I've seen for an early-stage product. However, **several critical issues require immediate attention before launch**, most notably:

1. **IRC §7216 consent structure likely does not satisfy regulatory requirements** — this carries criminal penalties
2. **Data retention periods are materially inconsistent across all four documents** — and also conflict with actual product behavior
3. **Encryption specifications in documents (AES-256) do not match actual implementation (AES-128-CBC/Fernet)** — this is a material misrepresentation
4. **Claude Vision OCR usage contradicts data minimization claims** — sending full W-2 images to the API sends SSNs, names, and financial data in a single API call, violating the WISP's own stated policy
5. **The product IS a "tax return preparer" under IRC §7701(a)(36)** regardless of disclaimers — PTIN and EFIN requirements apply

**Overall Assessment:** 🟡 YELLOW — Strong foundation, but critical regulatory issues (especially §7216 consent and encryption misrepresentation) must be resolved before any public launch or beta with real taxpayer data.

---

## Table of Contents

1. [WISP Review](#1-wisp-review)
2. [Privacy Policy Review](#2-privacy-policy-review)
3. [Terms of Service Review](#3-terms-of-service-review)
4. [User Consent Form Review](#4-user-consent-form-review)
5. [Cross-Document Consistency Check](#5-cross-document-consistency-check)
6. [Regulatory Compliance Matrix](#6-regulatory-compliance-matrix)
7. [Top 10 Priority Fixes](#7-top-10-priority-fixes)

---

## 1. WISP Review

### 🟢 GREEN (Adequate/Strong)

- **§1 Purpose & Scope:** Comprehensive scope definition. Correctly identifies all relevant data types, systems, personnel, and service providers. The explicit inclusion of "third-party APIs (including the Anthropic Claude API)" in scope is excellent.

- **§2 Regulatory Framework:** Correctly identifies GLBA, FTC Safeguards Rule, IRS Pub 4557, FTC Red Flags Rule, and state breach notification laws. The note that tax preparers are "financial institutions" under GLBA is accurate and important.

- **§3 Designated Security Coordinator:** Fully compliant with 16 CFR §314.4(a). Includes backup coordinator, clear responsibilities, reporting obligations to the Board/CEO, and explicit authority to act. The annual written report requirement (§3.2 item 6) satisfies the FTC's board reporting mandate.

- **§4 Definitions:** Clear, legally accurate definitions of Customer Information, FTI, NPI, Information System, Service Provider, and Security Event. Aligns with GLBA and IRS terminology.

- **§5 Risk Assessment:** Excellent structure. The 5×5 risk matrix with defined levels is standard and defensible. The Threat Matrix (§5.4.2) specifically addresses AI-unique risks (R-03: prompt injection, R-06: API data retention). Risk treatment options (§5.5) are complete.

- **§6 Security Six:** Thorough implementation of all six IRS Pub 4557 requirements (Firewalls, MFA, Encryption, Anti-Malware, Backups, Access Control). Each section includes specific technical controls, not just aspirational statements. The RBAC table in §6.6 is well-structured.

- **§7.3 Prompt Security:** Five specific controls for prompt injection prevention. This is a differentiator — most WISPs don't address AI-specific attack vectors at all.

- **§7.4 AI Output Review:** Validation against deterministic logic, user confirmation, audit trail, and confidence thresholds. This is the right approach for tax calculations.

- **§8 Employee Training:** Comprehensive training matrix with frequency, audience, and content requirements. Includes AI-specific training, which is unusual and commendable.

- **§9 Incident Response Plan:** Complete five-phase response process. IRS-specific reporting in §9.5 (TIGTA, local Stakeholder Liaison, Form 14039) is accurate and shows deep familiarity with IRS requirements.

- **§10 Service Provider Oversight:** Satisfies 16 CFR §314.4(f). Due diligence requirements include SOC 2 review, contractual obligations, and ongoing monitoring. The "no model training" requirement for Anthropic is explicitly called out.

- **§11 Data Retention & Destruction:** Comprehensive retention schedule with legal basis for each category. Destruction methods reference NIST SP 800-88. Legal hold procedures are included.

- **§12 Physical & Logical Security:** Cloud-native approach is properly addressed. Clean desk, full-disk encryption, no local storage, IaC, secrets management — all appropriate.

- **§13 Testing & Monitoring:** Includes penetration testing, vulnerability scanning, SIEM, and AI-specific testing. Remediation timelines are defined.

- **Appendix B & C:** IRS Pub 4557 and FTC Safeguards Rule crosswalks are excellent for audit preparedness.

### 🟡 YELLOW (Needs Improvement)

- **§2 Regulatory Framework — Missing IRC §7216/§6713:** The regulatory framework table omits IRC §7216 (criminal penalties for unauthorized disclosure of tax return information) and IRC §6713 (civil penalties). This is a significant omission for a tax preparation WISP. The WISP governs how tax data is handled internally, and §7216 should be the backdrop for every data handling decision.
  
  **Fix:** Add rows to the regulatory framework table:
  ```
  | IRC § 7216 | 26 U.S.C. § 7216 | Criminal penalties for unauthorized disclosure/use of tax return information |
  | IRC § 6713 | 26 U.S.C. § 6713 | Civil penalties for unauthorized disclosure/use of tax return information |
  | 26 CFR § 301.7216 | Treasury Regulations | Consent requirements for disclosure of tax return information |
  ```

- **§5.4.2 Threat Matrix — R-06 (Anthropic data retention):** Rated as Likelihood 1, Impact 5 = Risk Score 5 (Low). While Anthropic's API terms are favorable, this risk may be underrated. Anthropic retains data for up to 30 days for trust & safety, during which it could theoretically be subpoenaed or breached. For a service handling SSNs, consider rating this Medium (Likelihood 2 × Impact 5 = 10).

  **Fix:** Re-evaluate the likelihood score and document the rationale for the current rating. Consider adding a specific risk for "Anthropic policy change" (they could modify data handling terms).

- **§6.2 MFA — Session Timeout Placeholder:** The session timeout is listed as "[30 MINUTES]" in brackets, suggesting it's a placeholder. For a service handling SSNs and bank accounts, 30 minutes may be too long. IRS Pub 4557 and industry best practice for financial data suggest 15-20 minutes.

  **Fix:** Set session timeout to 15 minutes for pages displaying or processing sensitive financial data. Consider a longer timeout (30 min) for less sensitive pages.

- **§7.1 Data Flow Diagram:** The diagram shows the correct architecture but doesn't show Claude Vision as the OCR component. If Claude Vision is the primary OCR mechanism, full document images (containing SSNs) are being sent to the API — this should be explicitly shown in the data flow and addressed in §7.5.

  **Fix:** Update the data flow diagram to show image upload → Claude Vision API path. Add explicit notation about what data elements are present in sent images.

- **§7.2 Anthropic API — Action Items:** The three action items (DPA, zero-retention agreement, SOC 2 report review) are listed with unchecked boxes, indicating they haven't been completed. These are important pre-launch items.

  **Fix:** Complete these items before launch, especially the DPA. Document the status with dates.

- **§9.4 Phase 4 Notification — State Matrix:** The WISP references a "state notification matrix" as a separate document, but doesn't confirm it exists or provide even a summary. Given that ai-tax will have users across multiple states, this is a gap.

  **Fix:** Create the state notification matrix. At minimum, ensure Massachusetts (home state) and California (CCPA) breach notification requirements are documented in detail.

- **§11.1 Data Retention — Bank Account Info (120 days):** The retention period for bank account/routing numbers is stated as "Maximum 120 days." This seems long. If the purpose is solely to confirm refund deposit, 30-60 days should be sufficient.

  **Fix:** Consider reducing to 60 days. Document the business justification for 120 days if retained.

- **§13.1 AI-Specific Testing:** Listed as "annually + before major prompt changes." Given the critical nature of tax calculations, AI-specific testing (including prompt injection testing) should occur more frequently — at least quarterly during tax season (January–April).

  **Fix:** Increase frequency to quarterly during tax season, annually off-season. Add regression testing for tax calculation accuracy after any model version change (e.g., Claude Sonnet → Claude Opus).

- **§14.4 Related Documents:** References documents that may not yet exist (Risk Register, Incident Response Runbook, State Notification Matrix, Service Provider Register, Data Flow Diagrams, Employee Security Agreement). These need to be created before launch.

  **Fix:** Create each referenced document. At minimum, create stubs with "To Be Completed" and target dates.

### 🔴 RED (Critical Issues / Missing)

- **🔴 CRITICAL: Encryption Specification Mismatch (§6.3)**
  
  The WISP specifies "AES-256 encryption at rest" in multiple places (§6.3 At Rest section). The actual implementation uses **Fernet encryption (AES-128-CBC + HMAC-SHA256 with PBKDF2)**. AES-128 is still NIST-approved and considered secure, but **stating AES-256 when using AES-128 is a material misrepresentation** that could:
  
  - Create liability if a breach occurs and plaintiffs argue the security was misrepresented
  - Cause audit failures when inspectors compare documentation to implementation
  - Undermine credibility with regulators
  
  Additionally, Fernet uses CBC mode; the WISP doesn't mention the cipher mode or the HMAC component.
  
  **Fix (choose one):**
  1. **Upgrade implementation to AES-256-GCM** (preferred — matches documentation AND provides authenticated encryption)
  2. **Update all documentation** to accurately state: "AES-128-CBC with HMAC-SHA256 (via Fernet) using PBKDF2 key derivation"
  
  **Recommended language:** *"All stored personal data is encrypted at rest using Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256 for authentication), with encryption keys derived using PBKDF2. Keys are managed through [KMS/secrets manager]."*
  
  Note: If using Fernet, also document that Fernet tokens include a timestamp that enables key rotation verification.

- **🔴 CRITICAL: Data Retention Period Inconsistency (§11.1)**
  
  The WISP specifies **7-year retention** for tax returns and workpapers. However:
  - The Privacy Policy says **3 years**
  - The User Consent Form says **3 years**
  - The actual product implements **3 years for filed returns**, **30 days for active returns**, and **24 hours for uploads**
  
  A 7-year retention period has significant implications:
  - Increases breach exposure surface
  - Increases storage and compliance costs
  - Contradicts customer-facing promises
  - The IRS statute of limitations for standard returns is 3 years (6 years for substantial understatement)
  
  The WISP's 7-year figure appears to be based on IRS recommendations for preparers to retain workpapers, which is reasonable for a traditional tax preparer. But for a SaaS product, customer-facing documents must match operational reality.
  
  **Fix:** Align ALL documents to consistent retention periods. Recommended:
  - Uploaded source documents: 24 hours (as implemented) — document this as a security feature
  - Active/in-progress returns: 30 days
  - Filed returns: 3 years (matches IRS standard statute of limitations)
  - Workpapers/calculation logs: 3 years (consider 7 years if you want to match traditional preparer practices, but then update ALL documents)
  - If choosing 7 years, update Privacy Policy, Consent Form, and actual implementation

- **🔴 CRITICAL: Claude Vision OCR Contradicts Data Minimization Policy (§7.1, §7.5)**
  
  The WISP states in §7.1: *"OCR and field extraction happen on our infrastructure where possible, to minimize data sent to the API."* Section 7.5 states: *"Never send the following to the API in a single prompt: full SSN + full name + date of birth + bank account number."*
  
  However, the product uses **Claude Vision for OCR**. This means **full W-2 images** (containing SSN, full name, date of birth, employer info, wages, etc.) are sent to the Claude API in a single request. A W-2 image violates the §7.5 prohibition on sending "full SSN + full name" in a single prompt.
  
  **Fix (choose one):**
  1. **Implement local OCR first** (e.g., Tesseract, AWS Textract, Google Vision) to extract text, then send only extracted fields to Claude for interpretation — this would comply with the stated policy
  2. **Update the WISP to accurately describe the architecture** — acknowledge that Claude Vision processes full document images and implement compensating controls:
     - Log all Vision API calls with document metadata (not content)
     - Ensure Anthropic DPA/zero-retention is in place before sending images
     - Document the business justification for using Claude Vision vs. local OCR
     - Update §7.5's prohibition to account for Vision API usage with appropriate guardrails

- **🔴 MISSING: IRC §7216 / §6713 Coverage**
  
  As noted above, the WISP's regulatory framework completely omits IRC §7216 and §6713. For a tax preparation service, this is the most important data protection regulation — violation carries **criminal penalties** (up to $1,000 fine and 1 year imprisonment per violation under §7216). The WISP should:
  
  - Reference §7216/§6713 in the regulatory framework
  - Define "tax return information" per IRC §6103 / §7216 definitions
  - Document the specific consent mechanisms relied upon
  - Establish internal controls to prevent unauthorized disclosure/use
  - Train employees specifically on §7216 requirements
  
  **Fix:** Add §7216/§6713 to §2 Regulatory Framework. Add a new section (§7.6 or similar) titled "IRC §7216 Compliance" that documents consent mechanisms, prohibited uses, and internal controls.

- **🔴 MISSING: PTIN/EFIN Status**
  
  The WISP does not address the product's Preparer Tax Identification Number (PTIN) or Electronic Filing Identification Number (EFIN) status. Under IRC §6109(a)(4), any tax return preparer who prepares returns for compensation must have a PTIN. The product currently has no EFIN and can't e-file.
  
  **Fix:** Add a section documenting:
  - Current PTIN status of responsible individuals
  - EFIN application status and timeline
  - How the product operates in Phase 1 without e-filing capability (PDF/XML generation only)
  - The regulatory basis for operating without an EFIN in Phase 1

- **🔴 MISSING: Massachusetts 201 CMR 17.00 Specific Requirements**
  
  While the Privacy Policy references 201 CMR 17.00 compliance, the WISP (which IS the WISP required by 201 CMR 17.00) doesn't explicitly reference it in the regulatory framework or map its specific requirements. 201 CMR 17.04 requires:
  
  - Designation of employee(s) responsible for maintaining the WISP ✅ (§3)
  - Identifying and assessing internal/external risks ✅ (§5)
  - Developing security policies for employees ✅ (§8)
  - Imposing disciplinary measures for violations ✅ (§14.3)
  - Preventing terminated employee access ✅ (§6.6)
  - Oversight of third-party service providers ✅ (§10)
  - Restricting physical access to records ✅ (§12)
  - Monitoring, auditing, reviewing scope at least annually ✅ (§13.4)
  - Documenting responsive actions for incidents ✅ (§9)
  - Reasonable restrictions on physical access 🟡 (addressed as cloud-native)
  - Secure authentication protocols ✅ (§6.2)
  - Encryption of transmitted PI and PI on portable devices ✅ (§6.3)
  - Monitoring of systems for unauthorized access ✅ (§13.2)
  - Firewall protection ✅ (§6.1)
  - Up-to-date security patches 🟡 (not explicitly addressed)
  - Education and training ✅ (§8)
  
  **Fix:** Add 201 CMR 17.00 to §2 Regulatory Framework. Add an Appendix D crosswalk mapping 201 CMR 17.04 requirements to WISP sections (similar to Appendix B and C). Explicitly address security patch management.

---

## 2. Privacy Policy Review

### 🟢 GREEN (Adequate/Strong)

- **§2 Information We Collect:** Comprehensive and well-organized. Categories are clearly delineated (directly provided, automatically collected, third-party). The specific enumeration of tax form types (W-2, 1099 series, 1098 series, etc.) is good for transparency.

- **§3 How We Use Your Information:** Seven clearly stated purposes. The distinction between tax preparation, AI processing, and service improvement is important and well-drawn.

- **§4 Third-Party Data Processing — Anthropic:** The three-subsection structure (How Data is Processed, Anthropic's Data Practices, Data Minimization) provides appropriate transparency about AI data handling.

- **§5 Other Third-Party Data Sharing:** The table format listing each recipient, purpose, and data shared is clear and useful. The explicit statement "We do not sell your personal information" is important for CCPA compliance.

- **§7 Your Rights:** Comprehensive rights listing including access, correction, deletion, portability, restriction, objection, and consent withdrawal. The "Important Note" about tax law retention requirements is crucial and well-placed.

- **§8.3 Compliance with 201 CMR 17.00:** Explicitly lists all 201 CMR 17.04 requirements and affirms compliance. This is a strong section.

- **§9 Cookies and Analytics:** Clear table of cookie types. Explicit statement that tax data/SSNs are not shared with analytics providers.

- **§10 Children's Privacy:** Correct — the service should not be used by individuals under 18 (can't file returns independently in most cases).

- **§11 CCPA Notice:** Comprehensive CCPA section with categories, rights, authorized agents, and request procedures. The 45-day response timeline with 45-day extension is legally correct.

- **§12 Massachusetts Data Privacy:** References M.G.L. c. 93H breach notification requirements. Mentions AG and Director of Consumer Affairs notification — correct.

- **§14 Contact Us:** Includes complaint escalation paths to MA AG, FTC, and CA AG. This is a best practice.

- **§15 Changes to Privacy Policy:** 30-day notice with email and in-app notification. This is appropriate.

### 🟡 YELLOW (Needs Improvement)

- **§1 Introduction — "Agree to be bound":** The Privacy Policy states: *"By accessing or using the Service, you acknowledge that you have read, understood, and agree to be bound by this Privacy Policy."* Privacy policies are generally **informational disclosures**, not contractual agreements. Framing a privacy policy as binding can create complications:
  
  - The CCPA requires that privacy policies describe actual practices, not serve as consent mechanisms
  - Under GDPR (if ever applicable), privacy notices must be separate from consent
  - The FTC has taken the position that privacy policies are representations, and deceptive practices can be enforced regardless of "agreement"
  
  **Fix:** Change to: *"By accessing or using the Service, you acknowledge that you have read and understood this Privacy Policy, which describes how we collect, use, and protect your personal information."* Move consent mechanisms to the User Consent Form.

- **§4.2 Anthropic's Data Practices — Misleading Header:** The subsection header says *"No Data Retention by Anthropic"* but the body text states *"input and output data submitted through the API is retained by Anthropic for a limited period (typically up to 30 days)."* This is directly contradictory. A regulator or plaintiff's attorney would highlight this immediately.
  
  **Fix:** Change the bullet header to: *"Limited Data Retention by Anthropic"* or *"Anthropic Data Retention Period"*. Accurately describe the 30-day retention for trust & safety monitoring.

- **§6.1 Retention Periods — Tax Return Data:** States 3 years, with up to 6 years for amended returns or audits. This is legally defensible but should be aligned with the WISP (which says 7 years — see Cross-Document Consistency below).

- **§6.1 Retention Periods — Missing Categories:** The Privacy Policy doesn't specify retention periods for:
  - Bank account/routing numbers (WISP says 120 days)
  - Claude API call logs (WISP says 90 days redacted, 30 days with PII)
  - Security event logs (WISP says 3 years)
  
  **Fix:** Add these categories to §6.1 or reference the WISP's detailed retention schedule.

- **§8.1 Technical Safeguards — MFA "Encouraged":** States MFA is *"Available and strongly encouraged for all user accounts."* For a service handling SSNs and bank accounts, MFA should be **mandatory**, not merely encouraged. The FTC Safeguards Rule (16 CFR §314.4(c)(5)) requires MFA for "any individual accessing customer information" — while this technically refers to employees, making it mandatory for users accessing their own SSNs is a strong security posture.
  
  **Fix:** Change to: *"Multi-Factor Authentication is required for all user accounts that access sensitive tax information, including SSNs and bank account details."* At minimum, require MFA for any action that displays or transmits unmasked SSNs, bank account numbers, or completed tax returns.

- **§8.1 Technical Safeguards — Encryption Specifications:**
  - Claims TLS 1.3 — verify this is actually implemented. TLS 1.2 is the standard minimum; claiming 1.3 when serving TLS 1.2 is a misrepresentation.
  - Claims AES-256 — actual implementation is AES-128 (Fernet). See WISP §6.3 analysis above.
  
  **Fix:** Accurately describe the encryption in use. Use language like *"encrypted using industry-standard encryption (currently [actual cipher])"* to allow for upgrades without document amendments.

- **§11.1 CCPA Categories — Sensitive Personal Information:** The CCPA/CPRA created a specific category for "Sensitive Personal Information" with enhanced protections. The Privacy Policy lists it as a category but doesn't fully explain the enhanced protections or the right to limit processing of sensitive PI.
  
  **Fix:** Add a sentence in §11.2 explaining that users can direct the company to limit the use of Sensitive Personal Information to purposes that are necessary to perform the service. (The Right to Limit Use is listed, but the explanation of what it means is thin.)

- **§13 Do Not Track — Global Privacy Control:** The Privacy Policy only addresses "Do Not Track" browser signals. Under the CCPA/CPRA, **Global Privacy Control (GPC)** is a legally recognized opt-out mechanism. If a user sends a GPC signal, the business must treat it as a valid opt-out request.
  
  **Fix:** Add: *"We recognize Global Privacy Control (GPC) signals as valid opt-out requests under the California Consumer Privacy Act. When we detect a GPC signal, we will treat it as a request to opt out of the sale or sharing of personal information for that browser/device."* (Even if you don't sell data, you should acknowledge GPC.)

### 🔴 RED (Critical Issues / Missing)

- **🔴 CRITICAL: Encryption Misrepresentation (§8.1)**
  
  The Privacy Policy represents to consumers that their data is encrypted with "AES-256." The actual implementation uses AES-128 (Fernet). Under the FTC Act (15 U.S.C. §45), making material misrepresentations about security practices constitutes an unfair or deceptive practice. The FTC has brought enforcement actions for precisely this type of misrepresentation.
  
  **Risk:** FTC enforcement action, state AG enforcement, class action litigation citing deceptive practices.
  
  **Fix:** Immediately update to accurately describe the encryption. If you want to claim AES-256, upgrade the implementation first.

- **🔴 CRITICAL: Missing GLBA Privacy Notice Requirements**
  
  As a "financial institution" under GLBA (which the WISP correctly identifies in §2), the company must provide:
  
  1. **Initial privacy notice** at the time of establishing a customer relationship (12 CFR §1016.4)
  2. **Annual privacy notice** to customers (12 CFR §1016.5) — note: this requirement is waived if certain conditions are met under the FAST Act (2015), but the conditions must be verified
  3. **Opt-out notice** for sharing with non-affiliated third parties (12 CFR §1016.7)
  
  The current Privacy Policy may serve as the initial notice, but it doesn't explicitly identify itself as a GLBA privacy notice or include the required GLBA categories (e.g., categories of NPI shared with non-affiliated third parties, categories of affiliates and non-affiliates, opt-out procedures).
  
  **Fix:** Either:
  1. Add a section titled "GLBA Privacy Notice" that explicitly satisfies the Regulation P requirements, OR
  2. Create a separate GLBA Privacy Notice document
  
  Include: categories of NPI collected, categories shared with affiliates/non-affiliates, opt-out rights, confidentiality/security practices, and the required "Federal law gives you the right..." language.

- **🔴 MISSING: Disclosure of Tax Return Preparer Status**
  
  The Privacy Policy doesn't disclose the company's status as a tax return preparer under IRC §7701(a)(36). This is relevant because as a tax return preparer, the company has heightened obligations regarding the use and disclosure of tax return information. Users should understand that the company occupies this regulated role.
  
  **Fix:** Add a section (or to §1) explaining: *"As a tax return preparation service, [COMPANY NAME] is classified as a tax return preparer under Internal Revenue Code §7701(a)(36). This means we are subject to specific federal regulations governing the use and disclosure of your tax return information, including IRC §7216 and §6713."*

- **🔴 MISSING: Right to Opt Out of AI Processing**
  
  Several emerging state AI laws and the EU AI Act require disclosure of AI processing and, in some cases, an opt-out right. While the Privacy Policy discloses AI processing (§4), it does not provide any mechanism to opt out. Given that AI processing is essential to the service, an opt-out may not be feasible — but this should be explicitly addressed.
  
  Additionally, the CCPA's Right to Limit Use of Sensitive Personal Information could arguably extend to limiting AI processing of sensitive PI.
  
  **Fix:** Add a statement such as: *"AI processing via the Anthropic Claude API is an integral part of the Service and cannot be opted out of while using the Service. If you do not wish for your tax data to be processed by AI, you may choose not to use the Service."*

---

## 3. Terms of Service Review

### 🟢 GREEN (Adequate/Strong)

- **§1 Acceptance of Terms:** Clear, standard language. References Privacy Policy and applicable laws.

- **§2.2 Nature of the Service:** Strong disclaimer language. Multiple explicit statements that the service is not tax advice, not a CPA/EA/attorney, and doesn't guarantee accuracy. This is essential for liability limitation.

- **§3 Eligibility:** Appropriate age, SSN/ITIN, and legal authority requirements.

- **§4 User Responsibilities:** Comprehensive. The requirement to review all information before filing (§4.2) is critical — it puts the onus on the user and is the key defense against tax error liability. The explicit statement that "you, not the Service, are the taxpayer" is well-drafted.

- **§4.4 Prohibited Uses:** Good list including tax fraud, forged documents, reverse engineering, and unauthorized use on behalf of others.

- **§5 Disclaimers:** Strong disclaimer sections covering not-professional-advice, no accuracy guarantee, no refund guarantee, and IRS determination sovereignty. All-caps formatting for disclaimers is appropriate.

- **§6.3 Accuracy Guarantee — Limited Remedy:** This is well-structured. The conditions (accurate data, Service's error, filed as-prepared) and the cap ($500 or fees paid, whichever is less) provide a narrow but meaningful remedy. The 60-day notice requirement is reasonable.

- **§8 Intellectual Property:** Standard and appropriate. User retains ownership of their content. The limited license for processing is properly scoped.

- **§9 Fees and Payment:** Clear. 30-day refund policy with post-filing non-refundability is standard.

- **§10 Account Termination:** Balanced. User can close account, company can terminate for breach. Survival clause (§10.3) appropriately preserves disclaimers, liability limits, and dispute resolution.

- **§11 Dispute Resolution:** Well-structured arbitration clause with AAA, video conference option, class action waiver, small claims exception, governmental complaint carve-out, and 30-day opt-out. This is a strong, enforceable provision.

- **§13 General Provisions:** Standard boilerplate (entire agreement, severability, waiver, assignment, force majeure, notices, headings). All appropriate.

- **§14 Changes to Terms:** 30-day advance notice via email with required acceptance is appropriate.

### 🟡 YELLOW (Needs Improvement)

- **§2.1 Overview — E-Filing Reference:** States the service will *"Facilitate electronic filing of tax returns with the IRS and applicable state tax authorities (where supported)."* The product currently has no EFIN and can't e-file. Phase 1 generates PDF/XML only.
  
  **Fix:** Add a qualification: *"Facilitate electronic filing of tax returns with the IRS and applicable state tax authorities (where supported and when available). [Note: Electronic filing capability may not be available in all versions of the Service. Where e-filing is not available, the Service generates completed tax forms in PDF and/or XML format for manual filing or submission through another authorized e-file provider.]"*

- **§6.2 Cap on Liability — $100 Floor:** The liability cap of $100 or 12-month fees (whichever is greater) may be viewed as unconscionably low for a service that handles critical financial filings. If a tax calculation error causes a $50,000 penalty, a $100 cap could be challenged as unconscionable, particularly for consumer contracts.
  
  **Fix:** Consider increasing the floor to at least $500-$1,000 or removing the floor and relying solely on the fee-based cap. The §6.3 Accuracy Guarantee already provides a separate, limited remedy for calculation errors, which may be the more appropriate mechanism.

- **§6.1(b) Exclusion of Tax Authority Damages:** Excluding liability for "IRS or state tax authority adjustments, audits, penalties, interest, or additional tax assessments" is aggressive. While commonly used, this clause combined with §6.3's $500 cap means the company has virtually no liability for tax errors. A court may find this unconscionable for a consumer contract, especially one involving AI-generated tax calculations.
  
  **Fix:** Consider adding a more robust accuracy guarantee (§6.3) with a higher cap, or adding a penalty reimbursement program (similar to TurboTax/H&R Block "Maximum Refund Guarantee" or "Accuracy Guarantee") as a competitive and legal risk mitigation measure.

- **§7 IRC §7216 — Dual Consent Issue:** Section 7.2 says *"By using the Service and agreeing to these Terms and the separate User Consent Form..."* This creates confusion about where the actual §7216 consent resides. Is it in the ToS? The Consent Form? Both? The regulations require the consent to be clear and identifiable.
  
  **Fix:** Remove the §7216 consent from the ToS entirely. Keep only the reference to the separate User Consent Form. The ToS should state: *"Your use of the Service requires your separate consent under IRC §7216 for the disclosure of tax return information, which is obtained through the User Consent Form. Please review the User Consent Form carefully."*

- **§7.3 Consent Duration — Ambiguity:** States the consent is *"effective for the tax year for which you are preparing a return and remains in effect until you withdraw it in writing or your data is deleted."* This is ambiguous:
  - Does it expire at the end of the tax year?
  - Or does it persist until withdrawal/deletion?
  - If a user prepares a 2025 return and then returns in 2026, is a new consent required?
  
  26 CFR §301.7216-3(b)(4) requires that the consent identify a specific duration or state that it's valid until revoked.
  
  **Fix:** Choose one: (a) The consent is valid for the specific tax year and must be renewed each year (safer), or (b) The consent is valid until revoked in writing. Don't try to do both.

- **§8.4 Feedback License:** The "perpetual, irrevocable, worldwide, royalty-free license" for feedback is standard but may interact poorly with §7216. If user "feedback" includes any reference to their tax situation (e.g., "The service miscalculated my foreign tax credit"), that could be considered tax return information under §7216. Using it without proper consent would be a violation.
  
  **Fix:** Add a carve-out: *"This license does not apply to any tax return information as defined under IRC §7216. We will not use any feedback that contains or references your tax return information for any purpose other than addressing your specific concern."*

- **§13.5 Force Majeure — "IRS System Failures":** Including IRS system failures as a force majeure event is aggressive. If the IRS e-file system is down during filing season, the company should still make reasonable efforts to file returns by the deadline (paper filing, extension requests).
  
  **Fix:** Keep IRS system failures but add: *"provided that we will use commercially reasonable efforts to file returns by applicable deadlines through alternative means, including paper filing or extension requests, if IRS electronic systems are unavailable."*

### 🔴 RED (Critical Issues / Missing)

- **🔴 CRITICAL: Tax Return Preparer Status — Cannot Disclaim Away (§2.2)**
  
  Section 2.2 states: *"THE SERVICE IS A SOFTWARE TOOL DESIGNED TO ASSIST WITH TAX PREPARATION. IT IS NOT A SUBSTITUTE FOR PROFESSIONAL TAX ADVICE."* And: *"Is not a Certified Public Accountant (CPA), Enrolled Agent (EA), tax attorney, or licensed tax professional."*
  
  This disclaimer, while common in consumer tax software, does not change the legal reality: **Under IRC §7701(a)(36), any person who prepares for compensation, or employs persons to prepare for compensation, all or a substantial portion of any return of tax is a "tax return preparer."** A software tool that generates completed tax returns for a fee is a tax return preparer. TurboTax, H&R Block, and similar services are all tax return preparers despite being "software."
  
  The disclaimers appropriately set user expectations, but the company cannot disclaim its statutory obligations as a preparer, including:
  - PTIN requirements (IRC §6109(a)(4))
  - Due diligence requirements (IRC §6694, §6695)
  - Signing requirements (IRC §6695(b))
  - §7216/§6713 obligations
  - Record-keeping requirements
  
  **Risk:** If the company operates without PTINs, without satisfying preparer signing requirements, or without proper §7216 compliance, it faces penalties under §6695 ($50-$500 per return for various violations) and criminal liability under §7216.
  
  **Fix:** 
  1. Obtain PTINs for responsible individuals
  2. Comply with preparer signing requirements (software can sign using PTIN)
  3. Add a disclosure: *"[COMPANY NAME] is a tax return preparer as defined by IRC §7701(a)(36). The responsible individual for returns prepared through this Service is [NAME], PTIN [NUMBER]."*
  4. Do NOT remove the "not professional tax advice" disclaimers — they're still valuable for managing user expectations and limiting advisory liability

- **🔴 CRITICAL: IRC §7216 Consent Should Not Be in ToS (§7)**
  
  Including the §7216 consent within the Terms of Service (a document users must accept to use the service at all) creates a coercion problem. Under 26 CFR §301.7216-3(a)(3), the consent must be **knowing and voluntary**. If the user cannot use the service without accepting the ToS (which contains the §7216 consent), the consent is arguably not voluntary — it's a condition of service.
  
  The Treasury Regulations specifically envision §7216 consent as a **separate** document from the engagement letter (26 CFR §301.7216-3(b)(3)). Embedding it in the ToS arguably fails this requirement.
  
  **Risk:** Criminal penalties under §7216 for unauthorized disclosure if the consent is found invalid.
  
  **Fix:** 
  1. Remove §7216 consent language from the ToS
  2. Move it entirely to the User Consent Form (which must be separately signed/acknowledged)
  3. In the ToS, add only a reference: *"Use of the Service requires your separate consent under IRC §7216, which you will be asked to provide through the User Consent Form."*
  4. Ensure the Consent Form can be declined without preventing the user from accessing non-preparation features (e.g., account management, viewing past returns already filed)

- **🔴 MISSING: Preparer Penalties Disclosure (IRC §6694/§6695)**
  
  The ToS acknowledges §7216/§6713 penalties (§7.4) but does not address the company's obligations under:
  - **IRC §6694** — Penalties on preparers for understatement of tax ($1,000+ per return for unreasonable positions, $5,000+ for willful/reckless conduct)
  - **IRC §6695** — Penalties for failure to furnish copies, sign returns, furnish PTIN ($50-$500 per failure)
  
  These penalties apply regardless of disclaimers.
  
  **Fix:** Add a section or update §7.4 to acknowledge these obligations. This demonstrates good faith regulatory awareness and strengthens the company's position if ever challenged.

- **🔴 MISSING: State-Specific Tax Preparer Registration**
  
  Several states require tax preparer registration (California, Oregon, New York, Maryland, Connecticut, etc.). The ToS doesn't address multi-state registration requirements.
  
  **Fix:** Research state-specific preparer registration requirements. At minimum, add a statement like: *"[COMPANY NAME] complies with applicable state tax preparer registration requirements. The Service may not be available in jurisdictions where we are not registered."*

---

## 4. User Consent Form Review

### 🟢 GREEN (Adequate/Strong)

- **§1 Processing of Sensitive Personal Data:** Clear enumeration of data types collected. Covers SSN, income, tax documents, and bank information.

- **§2 AI Processing:** Good transparency about Claude API usage. The explicit statement that "Anthropic does NOT use my data to train their AI models" is important and correctly stated (for commercial API).

- **§3 Not Professional Tax Advice:** Repeats the critical disclaimer from ToS. Good to have it in the consent form where the user sees it at the point of consent.

- **§5 Data Retention:** States retention periods and destruction commitment.

- **§6 My Rights:** Lists access, correction, deletion, withdrawal, and portability rights.

- **Agreement Section:** Checkbox-based consent with separate items for Privacy Policy, data processing, AI disclaimer, and data retention. This is better than a single "I agree to everything" box.

### 🟡 YELLOW (Needs Improvement)

- **Form Title — Should Reference §7216:** The form title is "Consent for Processing of Tax Return Information." To satisfy 26 CFR §301.7216-3(b)(1), the consent should be clearly identified as an IRC §7216 consent. The title should reference §7216 explicitly.
  
  **Fix:** Change title to: *"Consent for Disclosure and Use of Tax Return Information Pursuant to Internal Revenue Code Section 7216"*

- **§2 AI Processing — Anthropic Data Retention:** States that data is "encrypted in transit and subject to Anthropic's commercial API data handling policies." Does not mention that Anthropic retains data for up to 30 days for trust & safety. Users consenting to disclosure should know where their data goes and how long it's held.
  
  **Fix:** Add: *"I understand that Anthropic may retain my data for up to 30 days for safety monitoring purposes, after which it is deleted."*

- **§4 IRS §7216 Consent — Scope Too Narrow:** The consent states disclosure is for the *"sole purpose of AI-assisted tax return preparation."* However, the service may also use tax return information for:
  - Error checking and quality assurance
  - Customer support (when the user asks for help)
  - Debugging API issues
  - Future year return preparation (if user returns)
  
  If tax return information is used for any purpose not covered by the consent, it's a §7216 violation.
  
  **Fix:** Broaden the purpose clause to include all legitimate uses: *"...for the purposes of AI-assisted tax return preparation, including document parsing, data extraction, calculation verification, error checking, quality assurance, and customer support related to my tax return."*

- **§4 IRS §7216 Consent — Missing "Right to Refuse" Statement:** Under 26 CFR §301.7216-3(b)(3), the consent must inform the taxpayer that they are not required to sign the consent. While §4 says "this consent is voluntary," it immediately adds "though doing so may prevent me from using the Service." This is technically accurate but the regulatory intent is to make clear that refusing consent doesn't prevent the preparer from preparing the return.
  
  The problem is unique to AI-tax: without Claude API disclosure, the service literally cannot function. In a traditional preparer scenario, the preparer can still prepare the return without disclosing to a third party.
  
  **Fix:** Add: *"I understand that I am not required to provide this consent. However, because the Service relies on AI processing via the Anthropic Claude API to function, declining this consent will prevent [COMPANY NAME] from preparing my tax return through this Service. I may choose to have my tax return prepared by another tax professional who does not use third-party AI processing."*

- **§5 Data Retention — Inconsistency:** States 3 years for tax returns. Must be aligned with the final retention period chosen across all documents.

- **Agreement Section — Not Separate for §7216:** The §7216 consent (item 2: "I voluntarily consent to the processing of my tax data as described above, including transmission to Anthropic's Claude API") is bundled with general data processing consent. Under 26 CFR §301.7216-3(b)(3), the §7216 consent should be on a separate page or clearly separated from other consents.
  
  **Fix:** Create a separate checkbox specifically for §7216 consent, visually distinguished from general data processing consent. Consider:
  ```
  ☐ [REQUIRED] I consent to the processing of my personal data as described in sections 1 and 3 above.
  
  --- IRC §7216 CONSENT (SEPARATE CONSENT REQUIRED) ---
  ☐ [REQUIRED] Pursuant to IRC §7216, I specifically consent to the disclosure of my tax return 
    information to Anthropic, Inc. via the Claude API for the purpose of AI-assisted tax return 
    preparation. I understand I am not required to sign this consent (see Section 4 above).
  
  ☐ I have read and understood the Privacy Policy and Terms of Service.
  ☐ I understand that ai-tax is not a tax professional and I am responsible for reviewing my return.
  ```

### 🔴 RED (Critical Issues / Missing)

- **🔴 CRITICAL: §7216 Consent Does Not Satisfy Regulatory Requirements**
  
  26 CFR §301.7216-3(b) requires the following elements for a valid §7216 consent. Current status:
  
  | Requirement | Regulation | Status |
  |---|---|---|
  | Name of tax return preparer | §301.7216-3(b)(1) | ❌ Missing — uses "[COMPANY NAME]" placeholder |
  | Specific taxpayer identified | §301.7216-3(b)(1) | ❌ Missing — no field for taxpayer name/SSN |
  | Tax return information to be disclosed | §301.7216-3(b)(2) | 🟡 Partial — listed in §1 but not specifically identified in §4 |
  | Purpose of disclosure | §301.7216-3(b)(2) | ✅ Stated |
  | Identity of recipient | §301.7216-3(b)(2) | ✅ "Anthropic, Inc." identified |
  | Taxpayer can refuse | §301.7216-3(b)(3) | 🟡 Says "voluntary" but undermined by "may prevent" language |
  | Consent document separate from engagement letter | §301.7216-3(b)(3) | 🟡 Partially — separate from ToS but bundles multiple consents |
  | Duration of consent | §301.7216-3(b)(4) | ❌ Missing — no specific duration or expiration |
  | Adequate identification as consent | §301.7216-3(b)(1) | 🟡 Not titled as §7216 consent |
  | Signature or electronic signature | §301.7216-3(b)(5) | 🟡 Checkbox — may suffice as e-sign but not explicitly stated |
  | Date of signature | §301.7216-3(b)(5) | ❌ Missing — no date field |
  
  **Risk:** If the consent is found to not comply with §301.7216-3(b), every disclosure to Anthropic is an unauthorized disclosure. Each violation carries up to $1,000 fine and 1 year imprisonment (§7216) plus $250 civil penalty (§6713).
  
  **Fix — Complete §7216 Consent Rewrite:**
  
  The §7216 consent section should be rewritten as a standalone, clearly delineated section with the following elements:
  
  ```markdown
  ## CONSENT FOR DISCLOSURE OF TAX RETURN INFORMATION
  ## (Required by Internal Revenue Code Section 7216)
  
  **Tax Return Preparer:** [COMPANY NAME], PTIN: [PTIN NUMBER]
  **Taxpayer Name:** [Auto-populated from account]
  **Taxpayer SSN (last 4):** XXX-XX-[Auto-populated]
  **Tax Year:** [Tax year being prepared]
  
  I, [TAXPAYER NAME], consent to the disclosure of my tax return information 
  to Anthropic, Inc. (Claude API) for the purpose of AI-assisted tax return 
  preparation, including document parsing, data extraction, and calculation 
  verification.
  
  **Tax return information to be disclosed includes:** Income and wage 
  information, filing status, deduction and credit information, tax form 
  data (W-2, 1099, 1098, and related schedules), and identifying information 
  necessary for tax return preparation. Social Security Numbers will be 
  minimized where technically feasible.
  
  **Duration:** This consent is effective for the [TAX YEAR] tax year 
  preparation period and expires on [DATE — e.g., October 15 of the 
  following year, or the extended filing deadline], or upon my written 
  revocation, whichever occurs first.
  
  **YOU ARE NOT REQUIRED TO SIGN THIS CONSENT.** Your tax return can 
  be prepared by another tax professional without this disclosure. However, 
  [COMPANY NAME] cannot provide its AI-assisted preparation service without 
  this disclosure.
  
  If you agree to the disclosure of your tax return information as described 
  above, sign or electronically acknowledge below.
  
  ☐ I consent to the disclosure described above.
  
  **Electronic Signature:** [Full Name]
  **Date:** [Auto-populated]
  ```

- **🔴 CRITICAL: No Taxpayer Identification in Consent**
  
  The consent form does not identify the specific taxpayer. Under §301.7216-3(b)(1), the consent must identify the taxpayer whose information is being disclosed. A generic form without the taxpayer's name is not a valid §7216 consent.
  
  **Fix:** Auto-populate the taxpayer's name (and last 4 of SSN for identification) from their account data. The consent must be specific to the individual.

- **🔴 CRITICAL: No Duration/Expiration**
  
  The consent form does not specify when the consent expires. 26 CFR §301.7216-3(b)(4) requires either a specific duration or a statement that the consent is valid until revoked.
  
  **Fix:** Add an expiration date. Recommended: *"This consent expires on [October 15 of the year following the tax year being prepared], or upon my written revocation, whichever occurs first."* The consent should be renewed each tax year.

- **🔴 MISSING: Consent for Data USE vs. Data DISCLOSURE**
  
  IRC §7216 distinguishes between **disclosure** (sharing with third parties) and **use** (using for purposes other than return preparation). The current consent addresses disclosure to Anthropic but doesn't explicitly consent to **use** of tax return information for purposes like:
  - Service improvement (even in anonymized/aggregated form)
  - Analytics
  - Future year return preparation suggestions
  - Marketing (if ever planned)
  
  If any of these uses occur, a separate §7216 **use** consent is required.
  
  **Fix:** If the company uses tax return information for any purpose beyond the specific return being prepared, add a separate **use consent** section. This is especially important for future commercialization plans. If no such uses occur, add a statement: *"[COMPANY NAME] does not use your tax return information for any purpose other than preparing your current tax return, except as required by law."*

- **🔴 MISSING: Consent for Disclosure to Cloud Provider**
  
  The §7216 consent only identifies Anthropic as a recipient. However, customer tax return information is also stored on the cloud hosting provider (AWS/GCP/Azure). Under strict §7216 interpretation, any third party that has access to (even encrypted) tax return information is a recipient requiring consent or a qualifying exception.
  
  Most practitioners rely on the **"auxiliary services" exception** (26 CFR §301.7216-2(d)) for cloud hosting, treating the cloud provider as providing auxiliary services comparable to a filing cabinet. This exception should be documented.
  
  **Fix:** Either:
  1. Add the cloud provider to the consent, OR
  2. Document reliance on the auxiliary services exception (§301.7216-2(d)) in the WISP, noting that the cloud provider stores only encrypted data and has no access to decrypted tax return information

---

## 5. Cross-Document Consistency Check

### Data Retention Periods

| Data Type | WISP §11.1 | Privacy Policy §6.1 | User Consent §5 | Actual Product | Consistent? |
|---|---|---|---|---|---|
| Filed tax returns | **7 years** | **3 years** | **3 years** | **3 years** | ❌ NO |
| Tax workpapers | **7 years** | Not specified | Not specified | Not specified | ❌ NO |
| Uploaded documents (W-2, etc.) | **3 years** | **3 years** | **3 years** | **24 hours** | ❌ NO |
| Account info after closure | **3 years** | **1 year** | **1 year** | Not specified | ❌ NO |
| Bank account numbers | **120 days** | Not specified | Not specified | Not specified | ❌ NO |
| API call logs (with PII) | **30 days** | Not specified | Not specified | Not specified | ❌ NO |
| Usage/log data | **1 year** | **12 months** | Not specified | Not specified | ✅ Yes |

**Action Required:** Choose ONE set of retention periods and apply consistently across all documents. Ensure actual product behavior matches documentation.

### Encryption Specifications

| Document | Encryption at Rest | Encryption in Transit | Actual |
|---|---|---|---|
| WISP §6.3 | AES-256 (KMS) | TLS 1.2+ (TLS 1.3 preferred) | AES-128-CBC (Fernet) |
| Privacy Policy §8.1 | AES-256 | TLS 1.3 | AES-128-CBC (Fernet) |
| Consent Form | Not specified | "Encrypted in transit" | AES-128-CBC (Fernet) |

**Action Required:** Align all documents to reflect actual encryption implementation. Either upgrade to AES-256 or update documentation.

### MFA Requirements

| Document | MFA Requirement |
|---|---|
| WISP §6.2 | Required for employees; required for customers |
| Privacy Policy §8.1 | "Available and strongly encouraged" for users |
| ToS | Not specified |
| Consent Form | Not specified |

**Action Required:** The WISP requires MFA for customers, but the Privacy Policy says it's merely "encouraged." Align — recommend making MFA mandatory.

### IRC §7216 Consent Location

| Document | §7216 Consent Content |
|---|---|
| ToS §7 | Full consent language with scope, limitations, revocability, penalties |
| User Consent Form §4 | Separate consent language |
| Privacy Policy | Brief mention of §7216 obligations |
| WISP | No mention of §7216 |

**Action Required:** Consolidate §7216 consent into the User Consent Form ONLY. Remove consent-obtaining language from ToS. The ToS should reference, not replicate, the consent.

### Cross-References Between Documents

| From | References | Valid Reference? |
|---|---|---|
| ToS §1 | Privacy Policy | ✅ Yes — `/docs/PRIVACY-POLICY.md` |
| ToS §7.2 | User Consent Form | ✅ Yes — `/docs/USER-CONSENT-FORM.md` |
| ToS §13.1 | Privacy Policy + User Consent Form | ✅ Yes |
| Privacy Policy §1 | No reference to ToS | 🟡 Should reference |
| Privacy Policy §8.3 | References WISP (implied) | 🟡 Not explicitly linked |
| User Consent Form | Privacy Policy + ToS | ✅ Yes |
| WISP §14.4 | References Privacy Policy | ✅ Yes |
| WISP | No reference to ToS or Consent Form | 🟡 Should reference |

**Action Required:** 
- Privacy Policy §1 should reference: *"This Policy is part of our Terms of Service and should be read in conjunction with our Terms of Service and User Consent Form."*
- WISP §14.4 Related Documents table should add entries for Terms of Service and User Consent Form.

### E-Filing References vs. Actual Capability

| Document | E-Filing Reference | Actual Status |
|---|---|---|
| WISP §7.1 | Implies e-filing capability | No EFIN — Phase 1 is PDF/XML only |
| Privacy Policy §5 | Lists "IRS / State Tax Authorities" as recipients for "Electronic filing" | No EFIN |
| ToS §2.1 | "Facilitate electronic filing" | No EFIN |
| ToS §7.2(3) | "Transmit your tax return to the IRS...for electronic filing" | No EFIN |

**Action Required:** All documents should clarify that e-filing may not be available in all versions/phases. Add conditional language: "where available" or "when electronic filing is supported."

---

## 6. Regulatory Compliance Matrix

### FTC Safeguards Rule (16 CFR Part 314)

| Requirement | Citation | Document Coverage | Status |
|---|---|---|---|
| Qualified individual | §314.4(a) | WISP §3 ✅ | ✅ Compliant |
| Written risk assessment | §314.4(b) | WISP §5 ✅ | ✅ Compliant |
| Safeguard design/implementation | §314.4(c) | WISP §6, §7, §12 ✅ | ✅ Compliant |
| Access controls | §314.4(c)(1) | WISP §6.6 ✅ | ✅ Compliant |
| System monitoring | §314.4(c)(2) | WISP §13.2 ✅ | ✅ Compliant |
| Encryption (transit + rest) | §314.4(c)(3) | WISP §6.3 ✅ (but see encryption mismatch) | 🟡 Docs say AES-256, reality is AES-128 |
| MFA | §314.4(c)(5) | WISP §6.2 ✅ | ✅ Compliant |
| Data retention limits | §314.4(c)(6) | WISP §11 ✅ (but inconsistent) | 🟡 Inconsistent across docs |
| Change management | §314.4(c)(8) | WISP §12.2 ✅ (IaC) | ✅ Compliant |
| Regular testing | §314.4(d) | WISP §13 ✅ | ✅ Compliant |
| Personnel training | §314.4(e) | WISP §8 ✅ | ✅ Compliant |
| Service provider oversight | §314.4(f) | WISP §10 ✅ | ✅ Compliant |
| Program evaluation/adjustment | §314.4(g) | WISP §13.4, §14 ✅ | ✅ Compliant |
| Incident response plan | §314.4(h) | WISP §9 ✅ | ✅ Compliant |
| Board reporting | §314.4(i) | WISP §3.2(6) ✅ | ✅ Compliant |

**Overall FTC Safeguards:** 🟢 Strong — The WISP substantially satisfies all FTC Safeguards Rule requirements. Primary issue is encryption specification accuracy.

### IRS Publication 4557

| Requirement | WISP Coverage | Status |
|---|---|---|
| Security Six | WISP §6 ✅ | ✅ Compliant |
| WISP existence | This document ✅ | ✅ Compliant |
| Risk assessment | WISP §5 ✅ | ✅ Compliant |
| Employee training | WISP §8 ✅ | ✅ Compliant |
| Data theft response | WISP §9 ✅ | ✅ Compliant |
| Report data theft to TIGTA | WISP §9.4, §9.5 ✅ | ✅ Compliant |
| Secure data disposal | WISP §11 ✅ | ✅ Compliant |
| Vet third-party providers | WISP §10 ✅ | ✅ Compliant |

**Overall IRS Pub 4557:** 🟢 Strong — Full coverage with detailed crosswalk in Appendix B.

### IRC §7216 / §6713

| Requirement | Coverage | Status |
|---|---|---|
| Valid written consent for disclosure | User Consent Form §4, ToS §7 | 🔴 Does not satisfy §301.7216-3(b) requirements |
| Consent identifies preparer | Not specified | 🔴 Missing |
| Consent identifies taxpayer | Not specified | 🔴 Missing |
| Consent specifies duration | Ambiguous | 🔴 Missing/Unclear |
| Consent specifies information disclosed | Partial (§1 lists categories) | 🟡 Needs strengthening |
| Consent is separate from engagement letter | Separate document exists but bundles consents | 🟡 Needs separation |
| Taxpayer informed can refuse | Says "voluntary" but undermined | 🟡 Needs revision |
| Consent for USE (not just disclosure) | Not addressed | 🔴 Missing |
| Auxiliary services exception documented | Not addressed | 🔴 Missing (for cloud provider) |
| Penalties acknowledged | ToS §7.4 ✅ | ✅ Compliant |

**Overall IRC §7216:** 🔴 CRITICAL — The consent structure likely does not satisfy Treasury Regulation requirements. This must be fixed before launch. Each non-compliant disclosure carries criminal liability.

### CCPA (California Consumer Privacy Act)

| Requirement | Coverage | Status |
|---|---|---|
| Categories of PI collected | Privacy Policy §11.1 ✅ | ✅ Compliant |
| Business/commercial purpose for collection | Privacy Policy §3 ✅ | ✅ Compliant |
| Categories of third parties shared with | Privacy Policy §5 ✅ | ✅ Compliant |
| Right to know | Privacy Policy §11.2 ✅ | ✅ Compliant |
| Right to delete | Privacy Policy §11.2 ✅ | ✅ Compliant |
| Right to correct | Privacy Policy §11.2 ✅ | ✅ Compliant |
| Right to opt out of sale/sharing | Privacy Policy §11.2 ✅ (states no sale) | ✅ Compliant |
| Right to limit sensitive PI use | Privacy Policy §11.2 ✅ | 🟡 Thin explanation |
| Right to non-discrimination | Privacy Policy §11.2 ✅ | ✅ Compliant |
| Authorized agents | Privacy Policy §11.3 ✅ | ✅ Compliant |
| Response timeline (45 days + 45 extension) | Privacy Policy §11.4 ✅ | ✅ Compliant |
| Global Privacy Control recognition | Not addressed | 🟡 Should be added |
| "Do Not Sell" link (if applicable) | Not applicable (no sale) | ✅ N/A |
| Financial incentive disclosure | Not addressed | 🟡 Add if offering discounts/promotions |
| Privacy policy updated annually | Privacy Policy §15 ✅ | ✅ Compliant |

**Overall CCPA:** 🟢 Substantially compliant. Minor gaps (GPC, sensitive PI detail).

### Massachusetts 201 CMR 17.00

| Requirement (17.04) | Coverage | Status |
|---|---|---|
| Designated security employee | WISP §3 ✅ | ✅ Compliant |
| Risk identification/assessment | WISP §5 ✅ | ✅ Compliant |
| Employee security policies | WISP §8 ✅ | ✅ Compliant |
| Disciplinary measures | WISP §14.3 ✅ | ✅ Compliant |
| Terminated employee access prevention | WISP §6.6 ✅ | ✅ Compliant |
| Third-party service provider oversight | WISP §10 ✅ | ✅ Compliant |
| Physical access restrictions | WISP §12 ✅ | ✅ Compliant |
| Annual monitoring/review | WISP §13.4 ✅ | ✅ Compliant |
| Incident response documentation | WISP §9 ✅ | ✅ Compliant |
| Secure authentication protocols | WISP §6.2 ✅ | ✅ Compliant |
| Encryption on public networks | WISP §6.3 ✅ | ✅ Compliant |
| Encryption on portable devices | WISP §12.1 ✅ | ✅ Compliant |
| System monitoring | WISP §13.2 ✅ | ✅ Compliant |
| Firewall protection | WISP §6.1 ✅ | ✅ Compliant |
| Security patches | Not explicitly addressed | 🟡 Should add patch management section |
| Malware protection | WISP §6.4 ✅ | ✅ Compliant |
| Employee education | WISP §8 ✅ | ✅ Compliant |

**Computer System Security Requirements (17.04(7)):**

| Requirement | Coverage | Status |
|---|---|---|
| Secure user authentication | WISP §6.2 ✅ | ✅ |
| Access control to PI on need-to-know | WISP §6.6 ✅ | ✅ |
| Encryption of PI transmitted wirelessly | WISP §6.3 ✅ | ✅ |
| Monitoring for unauthorized access | WISP §13.2 ✅ | ✅ |
| Encryption of PI on portable devices | WISP §12.1 ✅ | ✅ |
| Up-to-date firewall | WISP §6.1 ✅ | ✅ |
| Up-to-date patches | Not explicit | 🟡 |
| Up-to-date malware | WISP §6.4 ✅ | ✅ |

**Overall 201 CMR 17.00:** 🟢 Strong — One minor gap (explicit patch management). The Privacy Policy §8.3 explicitly lists all 17.04 requirements and affirms compliance.

### SOC 2 Readiness

| Trust Service Criteria | Document Coverage | Status |
|---|---|---|
| Security (Common Criteria) | WISP §6, §12, §13 | 🟡 Good foundation but not formally mapped to CC criteria |
| Availability | WISP §6.5 (backups), §13.2 (monitoring) | 🟡 No SLA defined |
| Processing Integrity | WISP §7.4 (AI output validation) | 🟡 Needs formal control documentation |
| Confidentiality | WISP §6.3, §6.6, §7 | 🟡 Good controls, needs formal policy |
| Privacy | Privacy Policy ✅ | 🟡 Needs mapping to TSC |

**Overall SOC 2:** 🟡 Not ready for audit, but strong foundation. Recommend engaging a SOC 2 readiness assessment firm when preparing for commercialization.

### Anthropic API Data Handling

| Concern | Coverage | Status |
|---|---|---|
| No-training guarantee documented | WISP §7.2, PP §4.2, UCF §2 ✅ | ✅ |
| 30-day retention acknowledged | WISP §7.2 ✅ | ✅ (but PP misleads — see §4.2 header issue) |
| DPA executed | WISP §7.2 — listed as action item | 🔴 Not yet done |
| Zero-retention agreement | WISP §7.2 — listed as action item | 🔴 Not yet done |
| SOC 2 report reviewed | WISP §7.2 — listed as action item | 🔴 Not yet done |
| Data minimization | WISP §7.5, PP §4.3, UCF §2 ✅ | 🟡 Contradicted by Claude Vision usage |
| Anthropic policy change risk | WISP §5.4.2 R-06 | 🟡 Underrated risk |

**Overall Anthropic API:** 🟡 Well-documented but three critical action items are incomplete, and data minimization claims are contradicted by Claude Vision OCR usage.

---

## 7. Top 10 Priority Fixes

### Priority 1: 🔴 Restructure IRC §7216 Consent (CRIMINAL LIABILITY)

**Documents:** User Consent Form (primary), Terms of Service (remove consent)
**Risk:** Every API call to Anthropic with tax return information is potentially an unauthorized disclosure carrying criminal penalties ($1,000 fine + 1 year imprisonment per violation under §7216, $250 civil penalty per violation under §6713).
**Fix:** Rewrite §7216 consent per §301.7216-3(b) requirements: preparer identification, taxpayer identification, specific information identified, duration/expiration, right-to-refuse statement, separate acknowledgment, date. Remove consent from ToS.

### Priority 2: 🔴 Fix Encryption Misrepresentation (FTC DECEPTION RISK)

**Documents:** WISP §6.3, Privacy Policy §8.1
**Risk:** Claiming AES-256 when using AES-128 (Fernet) is a material misrepresentation under FTC Act §5. Could trigger enforcement action, class action, and audit failure.
**Fix:** Either upgrade to AES-256-GCM or update all documents to accurately state AES-128-CBC with HMAC-SHA256 (Fernet).

### Priority 3: 🔴 Resolve Data Retention Inconsistencies

**Documents:** All four — WISP, Privacy Policy, User Consent Form, ToS
**Risk:** Inconsistent retention periods (7 years vs. 3 years vs. 24 hours) create regulatory confusion, breach exposure, and potential breach of contract with customers.
**Fix:** Establish one canonical retention schedule. Apply it to all documents. Ensure product implementation matches.

### Priority 4: 🔴 Resolve Claude Vision OCR vs. Data Minimization Contradiction

**Documents:** WISP §7.1, §7.5
**Risk:** If the WISP prohibits sending full SSN + name in a single API call, but Claude Vision processes full W-2 images (which contain both), the company is violating its own security policy. In a breach investigation, this inconsistency would be damaging.
**Fix:** Either implement local OCR first (compliant with policy) or update the policy to accurately describe Claude Vision usage with compensating controls.

### Priority 5: 🔴 Address Tax Return Preparer Status

**Documents:** Terms of Service §2.2
**Risk:** The product IS a tax return preparer under IRC §7701(a)(36) regardless of disclaimers. Operating without PTINs and without complying with preparer requirements exposes the company to penalties under §6694, §6695, and potential injunction.
**Fix:** Obtain PTINs, comply with preparer signing requirements, add preparer identification to documents.

### Priority 6: 🔴 Add GLBA Privacy Notice Requirements

**Documents:** Privacy Policy
**Risk:** As a "financial institution" under GLBA, the company must provide initial and (potentially) annual privacy notices with specific content requirements. The current privacy policy doesn't satisfy GLBA/Regulation P requirements.
**Fix:** Add GLBA Privacy Notice section to Privacy Policy or create separate notice.

### Priority 7: 🟡 Execute Anthropic DPA and Zero-Retention Agreement

**Documents:** WISP §7.2 (action items)
**Risk:** Without a DPA, the company has limited contractual recourse if Anthropic experiences a breach affecting customer data. Without zero-retention, Anthropic holds tax return information for 30 days.
**Fix:** Execute DPA before launch. Request zero-retention agreement.

### Priority 8: 🟡 Clarify E-Filing Status Across All Documents

**Documents:** WISP, Privacy Policy, ToS
**Risk:** Documents reference e-filing capability that doesn't exist yet. If users rely on e-filing that isn't available, it could be a deceptive practice claim.
**Fix:** Add "where available" qualifiers to all e-filing references. Explicitly state Phase 1 generates PDF/XML only.

### Priority 9: 🟡 Make MFA Mandatory for Customer Accounts

**Documents:** Privacy Policy §8.1
**Risk:** "Encouraged" MFA for accounts containing SSNs and bank data is below industry standard and may not satisfy FTC Safeguards Rule's "access controls" requirement.
**Fix:** Require MFA for all customer accounts, or at minimum for any action that reveals unmasked SSNs or bank account numbers.

### Priority 10: 🟡 Add Missing §7216 USE Consent + Cloud Provider Exception

**Documents:** User Consent Form
**Risk:** The §7216 consent only covers disclosure to Anthropic. It doesn't cover use of tax data for service improvement, analytics, or future year suggestions. Cloud provider storage isn't addressed.
**Fix:** Add use consent if any non-preparation uses exist. Document reliance on auxiliary services exception (§301.7216-2(d)) for cloud storage.

---

## Appendix: Additional Findings (Lower Priority)

### A. Missing Patch Management Policy
**Document:** WISP
**Issue:** No explicit section on security patch management and timelines. 201 CMR 17.04(7)(c) requires "up-to-date security patches."
**Fix:** Add a subsection to §6 or §13 on patch management: critical patches within 72 hours, high within 2 weeks, medium within 30 days.

### B. Placeholder Fields
**All Documents:** Numerous `[PLACEHOLDER]` fields need to be filled before launch (company name, addresses, coordinator names, dates, etc.). These are not legal issues but operational readiness items.

### C. Accessibility Compliance
**All Documents:** No mention of ADA/WCAG accessibility. Tax preparation services must be accessible to users with disabilities. Consider adding an accessibility commitment.

### D. International Data Transfers
**Privacy Policy:** Does not address whether data is processed or stored outside the United States. If using cloud regions outside the US, or if Anthropic processes data in non-US regions, international data transfer provisions may be needed.

### E. Biometric Data
**Privacy Policy:** If Claude Vision processes user photographs or identity documents (not just tax forms), biometric data laws (Illinois BIPA, Texas CUBI) may apply. Currently not addressed.

### F. FTC Identity Theft Red Flags Rule
**WISP §2:** Lists the Red Flags Rule but doesn't implement it. Should add a section or reference a separate Identity Theft Prevention Program (ITPP).

### G. State Tax Preparer Registration
**ToS:** California (CTEC registration), Oregon, New York, Maryland, and Connecticut require tax preparer registration. The company should research and comply before accepting users from these states.

### H. Consumer Financial Protection Bureau (CFPB)
**Privacy Policy:** No mention of CFPB. Depending on the company's revenue and transaction volume, CFPB oversight may apply for certain consumer financial products or services.

### I. Insurance
**WISP §5.5:** Mentions risk transfer via insurance but doesn't specify required coverage. Recommend:
- Professional liability / errors & omissions (E&O) insurance
- Cyber liability insurance
- General liability insurance

### J. Terms of Service — Age of Majority
**ToS §3:** Requires users to be 18+. Note that the age of majority is 19 in Alabama and Nebraska, and 21 in Mississippi. Consider: "at least eighteen (18) years of age (or the age of majority in your state of residence, whichever is greater)."

---

## Conclusion

The ai-tax legal documentation demonstrates a strong foundation, particularly in the WISP's treatment of FTC Safeguards Rule requirements and AI-specific data handling. The level of detail and AI-specific risk assessment is above average for an early-stage product.

However, **the IRC §7216 compliance gap is the most urgent issue** and must be resolved before any real taxpayer data is processed. The criminal penalties for unauthorized disclosure are not theoretical — the IRS has referred §7216 cases for prosecution. The encryption misrepresentation and data retention inconsistencies are the next most critical fixes.

**Recommended next steps:**
1. Fix Priorities 1–6 immediately (before any beta/launch with real taxpayer data)
2. Engage a tax attorney with §7216 expertise to review the revised consent form
3. Engage a data privacy attorney to review the GLBA notice and CCPA compliance
4. Complete the Anthropic DPA and zero-retention agreement
5. Obtain PTINs and address preparer registration requirements
6. Fix Priorities 7–10 before public launch
7. Address Appendix items during commercialization preparation

---

*This review was prepared by an AI legal review agent and is not a substitute for advice from a licensed attorney. The analysis is based on publicly available legal requirements and best practices as of February 2026. All recommendations should be reviewed by qualified legal counsel before implementation.*

*Reviewed: WISP.md, PRIVACY-POLICY.md, TERMS-OF-SERVICE.md, USER-CONSENT-FORM.md*
