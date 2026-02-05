# Written Information Security Plan (WISP)

**[COMPANY NAME]**
**AI-Tax — AI-Powered Tax Preparation Service**

| Field | Value |
|---|---|
| Document Version | 1.0 |
| Effective Date | [EFFECTIVE DATE] |
| Last Revised | [REVISION DATE] |
| Next Scheduled Review | [EFFECTIVE DATE + 12 months] |
| Classification | Confidential — Internal Use Only |
| Approved By | [SECURITY COORDINATOR NAME], Designated Security Coordinator |

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Regulatory Framework](#2-regulatory-framework)
3. [Designated Security Coordinator](#3-designated-security-coordinator)
4. [Definitions](#4-definitions)
5. [Risk Assessment](#5-risk-assessment)
6. [Security Six Implementation](#6-security-six-implementation)
7. [AI-Specific Data Handling](#7-ai-specific-data-handling)
8. [Employee Training & Awareness](#8-employee-training--awareness)
9. [Incident Response Plan](#9-incident-response-plan)
10. [Service Provider Oversight](#10-service-provider-oversight)
11. [Data Retention & Destruction Policy](#11-data-retention--destruction-policy)
12. [Physical & Logical Security](#12-physical--logical-security)
13. [Testing & Monitoring](#13-testing--monitoring)
14. [Policy Governance](#14-policy-governance)
15. [Signature Page](#15-signature-page)

---

## 1. Purpose & Scope

### 1.1 Purpose

This Written Information Security Plan ("WISP" or "Plan") describes the administrative, technical, and physical safeguards that [COMPANY NAME] ("Company," "we," "us") maintains to protect the security, confidentiality, and integrity of customer information, including federal tax information (FTI) and personally identifiable information (PII), collected and processed through the AI-Tax platform.

### 1.2 Scope

This Plan applies to:

- **All customer information** collected, processed, stored, or transmitted by AI-Tax, including but not limited to Social Security Numbers (SSNs), Employer Identification Numbers (EINs), income data, bank account and routing numbers, and tax return data.
- **All systems** that touch customer data, including our web application, backend infrastructure, cloud hosting, third-party APIs (including the Anthropic Claude API), databases, and logging systems.
- **All personnel** — employees, contractors, and any person with access to customer information or systems that process it.
- **All service providers** who receive, maintain, process, or otherwise have access to customer information on our behalf.

### 1.3 Commitment

[COMPANY NAME] is committed to maintaining the confidentiality of customer tax data entrusted to us. We treat every SSN, every W-2, and every piece of financial data as if it were our own. This Plan is not a checkbox exercise — it is the operational security standard we hold ourselves to.

---

## 2. Regulatory Framework

This WISP is designed to satisfy the requirements of:

| Regulation | Citation | Key Requirement |
|---|---|---|
| **FTC Safeguards Rule** | 16 CFR Part 314 (as amended 2023) | Comprehensive information security program for financial institutions |
| **Gramm-Leach-Bliley Act (GLBA)** | 15 U.S.C. §§ 6801–6809 | Protect nonpublic personal information (NPI) of consumers |
| **IRC § 7216** | 26 U.S.C. § 7216; 26 CFR § 301.7216 | Criminal penalties for unauthorized disclosure/use of tax return information |
| **IRC § 6713** | 26 U.S.C. § 6713 | Civil penalties for unauthorized disclosure/use of tax return information |
| **IRS Publication 4557** | Safeguarding Taxpayer Data | Security recommendations for tax professionals |
| **IRS Revenue Procedure 98-25** | Electronic record-keeping | Requirements for maintaining electronic tax records |
| **FTC Identity Theft Red Flags Rule** | 16 CFR Part 681 | Detect, prevent, and mitigate identity theft |
| **Massachusetts 201 CMR 17.00** | M.G.L. c. 93H | Written Information Security Program (WISP) requirements for MA residents' PI |
| **State Breach Notification Laws** | Varies by state | Timely notification of data breaches to affected individuals and regulators |

Tax preparers are classified as **financial institutions** under the GLBA and are therefore subject to the FTC Safeguards Rule. This is not optional.

---

## 3. Designated Security Coordinator

### 3.1 Appointment

Pursuant to 16 CFR § 314.4(a), [COMPANY NAME] designates the following individual as its **Qualified Security Coordinator**:

| Role | Details |
|---|---|
| **Name** | [SECURITY COORDINATOR NAME] |
| **Title** | [TITLE, e.g., Chief Technology Officer] |
| **Email** | [SECURITY EMAIL] |
| **Phone** | [PHONE NUMBER] |
| **Backup Coordinator** | [BACKUP COORDINATOR NAME] |

### 3.2 Responsibilities

The Security Coordinator is responsible for:

1. **Implementation** — Overseeing day-to-day implementation of this WISP.
2. **Risk Assessment** — Conducting or supervising annual risk assessments (Section 5).
3. **Vendor Management** — Evaluating and monitoring service providers (Section 10).
4. **Incident Response** — Serving as incident commander during security events (Section 9).
5. **Training** — Ensuring all personnel complete required security training (Section 8).
6. **Reporting** — Providing written security status reports to the Board (or CEO for startups without a Board) at least annually, covering:
   - Overall status of the information security program
   - Material matters related to the program (risk assessments, security events, violations, recommendations)
   - Compliance status with this Plan
7. **Regulatory Liaison** — Serving as primary contact for IRS, FTC, and state regulator inquiries.
8. **Plan Maintenance** — Reviewing and updating this WISP at least annually or after any material change to operations, threats, or technology.

### 3.3 Authority

The Security Coordinator has the authority to:

- Approve or deny access to customer information systems.
- Require immediate remediation of identified vulnerabilities.
- Suspend system access for any user pending investigation.
- Engage external security consultants as needed.
- Escalate security matters directly to the CEO / Board.

---

## 4. Definitions

| Term | Definition |
|---|---|
| **Customer Information** | Any record containing nonpublic personal information (NPI) about a customer, whether in paper, electronic, or other form. For AI-Tax, this includes tax documents, SSNs, income data, bank information, and tax return calculations. |
| **Federal Tax Information (FTI)** | Tax return information, as defined in IRC § 6103, received directly or indirectly from the IRS. |
| **Nonpublic Personal Information (NPI)** | Personally identifiable financial information provided by a consumer, resulting from a transaction, or otherwise obtained by the Company. (GLBA definition.) |
| **Information System** | Any discrete set of electronic information resources organized for the collection, processing, maintenance, use, sharing, dissemination, or disposition of customer information. |
| **Service Provider** | Any person or entity that receives, maintains, processes, or otherwise has access to customer information through its provision of services directly to [COMPANY NAME]. |
| **Security Event** | Any actual or suspected unauthorized access to, or acquisition, use, or disclosure of, customer information. |

---

## 5. Risk Assessment

### 5.1 Overview

Pursuant to 16 CFR § 314.4(b), [COMPANY NAME] conducts periodic risk assessments to identify reasonably foreseeable internal and external risks to the security, confidentiality, and integrity of customer information. Risk assessments evaluate the sufficiency of current safeguards and drive remediation priorities.

### 5.2 Assessment Frequency

- **Full Assessment:** Annually, or upon material change to systems, operations, or threat landscape.
- **Targeted Assessment:** Upon introduction of new technology, vendors, or data flows (e.g., new AI model integration).
- **Continuous:** Ongoing monitoring through automated tooling (see Section 13).

### 5.3 Methodology

Each risk is evaluated on:

- **Likelihood** (1–5): How probable is this event?
- **Impact** (1–5): How severe would the consequences be?
- **Risk Score** = Likelihood × Impact (1–25)
- **Risk Level:** Low (1–6), Medium (7–12), High (13–19), Critical (20–25)

### 5.4 Identified Risks — Customer Tax Data

The following table identifies key risks to the categories of customer information handled by AI-Tax:

#### 5.4.1 Data Categories at Risk

| Data Category | Examples | Sensitivity |
|---|---|---|
| **Social Security Numbers** | SSN, ITIN, EIN | Critical — enables identity theft |
| **Income Information** | W-2 wages, 1099 income, K-1 distributions | High |
| **Bank Account Information** | Account numbers, routing numbers (for direct deposit refunds) | Critical — enables financial fraud |
| **Tax Return Data** | Calculated tax liability, deductions, credits, filing status | High |
| **Uploaded Documents** | Scanned W-2s, 1099s, receipts | High — may contain all of the above |
| **Authentication Credentials** | Passwords, MFA tokens, session tokens | Critical |

#### 5.4.2 Threat Matrix

| # | Threat | Category | Likelihood | Impact | Risk Score | Mitigation Reference |
|---|---|---|---|---|---|---|
| R-01 | Unauthorized access to database containing SSN/bank data | External attack | 3 | 5 | **15 (High)** | §6.1, §6.3, §6.6 |
| R-02 | Credential compromise (phishing, password reuse) | External / Human | 4 | 5 | **20 (Critical)** | §6.2, §8 |
| R-03 | Data exfiltration via Claude API prompt injection | AI-specific | 2 | 5 | **10 (Medium)** | §7.3, §7.4 |
| R-04 | Insider threat — employee accesses data without authorization | Internal | 2 | 5 | **10 (Medium)** | §6.6, §8, §13.3 |
| R-05 | Data exposure through application vulnerability (SQLi, XSS) | External attack | 3 | 5 | **15 (High)** | §6.1, §13.1 |
| R-06 | Anthropic API data retention / training use | Vendor risk | 1 | 5 | **5 (Low)** | §7.2, §10 |
| R-07 | Loss of data availability (ransomware, infrastructure failure) | External / Ops | 2 | 4 | **8 (Medium)** | §6.5, §9 |
| R-08 | Interception of data in transit | External attack | 2 | 5 | **10 (Medium)** | §6.3 |
| R-09 | Improper data retention beyond required period | Compliance | 3 | 3 | **9 (Medium)** | §11 |
| R-10 | Cloud hosting misconfiguration (S3 bucket, open ports) | Operational | 3 | 5 | **15 (High)** | §6.1, §12.2, §13.1 |
| R-11 | Session hijacking or token theft | External attack | 3 | 4 | **12 (Medium)** | §6.2, §6.3 |
| R-12 | Tax preparer identity fraud (fake PTIN/EFIN usage) | Fraud | 2 | 4 | **8 (Medium)** | §8, §13 |

### 5.5 Risk Treatment

Each identified risk must have a documented treatment plan:

- **Mitigate** — Implement controls to reduce likelihood or impact.
- **Transfer** — Shift risk via insurance or contractual allocation.
- **Accept** — Formally accept risk with documented justification and executive sign-off.
- **Avoid** — Eliminate the activity that creates the risk.

The Security Coordinator maintains the **Risk Register** (separate working document) with assigned owners, target dates, and status for each risk treatment.

---

## 6. Security Six Implementation

IRS Publication 4557 identifies six critical security measures ("Security Six") required for tax professionals. This section documents how [COMPANY NAME] implements each one, plus additional controls required by the FTC Safeguards Rule.

### 6.1 Firewalls & Network Security

**Requirement:** Protect the network perimeter and internal segments from unauthorized access.

**Implementation:**

- **Cloud Provider Firewalls:** All infrastructure runs on [CLOUD PROVIDER, e.g., AWS / GCP / Azure]. We leverage the provider's network security groups / firewall rules to restrict inbound and outbound traffic.
- **Default Deny:** All security groups follow a default-deny policy. Only explicitly required ports and protocols are permitted.
- **Web Application Firewall (WAF):** A WAF (e.g., AWS WAF, Cloudflare) protects the AI-Tax web application against OWASP Top 10 threats, including SQL injection, XSS, and request forgery.
- **Network Segmentation:** Production databases are isolated in private subnets with no direct internet access. API servers communicate with databases through internal networking only.
- **Egress Filtering:** Outbound traffic is restricted to known-good destinations (Anthropic API endpoints, IRS e-file systems, payment processors).
- **DDoS Protection:** Cloud-native DDoS mitigation is enabled on all public-facing endpoints.

**Review:** Firewall rules are reviewed quarterly and after any infrastructure change. Unused rules are removed.

### 6.2 Multi-Factor Authentication (MFA)

**Requirement:** Require MFA for all access to systems containing customer information.

**Implementation:**

- **Employee Access:** All employees and contractors must use MFA (TOTP or hardware security key; SMS is **not** permitted as a sole factor) to access:
  - Cloud provider console (AWS/GCP/Azure)
  - Production systems (SSH, VPN, bastion hosts)
  - Code repositories
  - Internal admin tools
  - Email and collaboration tools
- **Customer Access:** AI-Tax users authenticate with MFA (email/phone verification + TOTP or passkey) before accessing their tax data.
- **API Authentication:** Internal service-to-service communication uses mutual TLS (mTLS) or signed JWTs — not shared API keys.
- **Privileged Access:** Administrative accounts require hardware security keys (FIDO2/WebAuthn).
- **Session Management:** Sessions expire after [30 MINUTES] of inactivity. Re-authentication is required for sensitive operations (downloading returns, changing bank info).

### 6.3 Encryption

**Requirement:** Encrypt customer information in transit and at rest.

**Implementation:**

#### In Transit
- **TLS 1.2+** on all external connections. TLS 1.3 preferred. Older protocols (SSL, TLS 1.0/1.1) are disabled.
- **HSTS** (HTTP Strict Transport Security) enforced with a minimum max-age of 1 year, including subdomains.
- **API calls to Anthropic Claude** use TLS 1.2+ exclusively. API keys are transmitted only in encrypted headers.
- **Certificate management** via automated issuance and renewal (e.g., Let's Encrypt / AWS ACM).

#### At Rest
- **Database encryption:** All databases use AES-256-GCM encryption at rest, managed by the cloud provider's KMS (Key Management Service).
- **File storage:** Uploaded tax documents (W-2, 1099 images/PDFs) are encrypted at rest using AES-256-GCM in the object storage layer (e.g., S3 SSE-KMS).
- **Application-layer encryption:** User tax data is additionally encrypted at the application layer using AES-256-GCM with PBKDF2 key derivation (600,000 iterations) before storage.
- **Backups** are encrypted with a separate KMS key.
- **SSN storage:** SSNs are stored in a dedicated, separately-encrypted column/field. Full SSNs are displayed only as masked values (XXX-XX-1234) in the application UI, with full values accessible only during IRS e-file transmission.

#### Key Management
- Encryption keys are managed through the cloud provider's KMS. Keys are rotated annually (automated).
- No encryption keys are stored in source code, environment variables, or configuration files. Secrets are managed via a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault).
- Access to KMS is logged and restricted to the minimum required roles.

### 6.4 Anti-Malware / Endpoint Protection

**Requirement:** Protect systems from malicious software.

**Implementation:**

- **Server-Side:** All production servers run an endpoint detection and response (EDR) agent (e.g., CrowdStrike, SentinelOne) with real-time monitoring and automatic quarantine.
- **Uploaded File Scanning:** All files uploaded by users (W-2 images, PDFs, etc.) are scanned for malware before processing. Infected files are quarantined and the upload is rejected.
- **Employee Endpoints:** All company-issued devices run EDR software with:
  - Real-time scanning
  - Automatic signature updates
  - USB storage restrictions
  - Full-disk encryption (FileVault / BitLocker)
- **Container Security:** Production container images are scanned for known vulnerabilities before deployment (e.g., Trivy, Snyk Container).

### 6.5 Backups

**Requirement:** Maintain secure, recoverable backups of customer data.

**Implementation:**

- **Database Backups:** Automated daily backups with point-in-time recovery enabled (minimum 30-day retention).
- **Backup Encryption:** All backups are encrypted at rest using AES-256-GCM with dedicated KMS keys.
- **Backup Location:** Backups are stored in a separate cloud region from production to protect against regional outages.
- **Backup Testing:** Recovery tests are performed quarterly. Results are documented, including recovery time achieved.
- **Immutability:** Backup storage uses write-once-read-many (WORM) or object lock to prevent ransomware from deleting or encrypting backups.
- **Access Control:** Backup restoration requires the Security Coordinator's approval and MFA authentication.

### 6.6 Access Control

**Requirement:** Limit access to customer information to only those with a legitimate business need.

**Implementation:**

#### Principle of Least Privilege
- Every user, system, and service account is granted the minimum permissions necessary to perform its function.
- Access to customer data (especially SSN, bank info) is restricted to roles that specifically require it. Most engineers do not need and do not have access to production customer data.

#### Role-Based Access Control (RBAC)

| Role | Access Level | Customer Data Access |
|---|---|---|
| Customer (end user) | Own data only | Yes — own records only |
| Support Agent | Read-only, scoped | Masked SSN, no bank details unless escalated |
| Engineer — Application | Code, staging environment | No production customer data |
| Engineer — Infrastructure | Production systems, logs | Access to encrypted data; decryption requires approval |
| Security Coordinator | Full administrative | Full access with audit logging |
| CEO / Executive | Policy and compliance | Reports only — no direct system access |

#### Access Lifecycle
- **Provisioning:** Access requests are documented and approved by the Security Coordinator before granting.
- **Review:** All access privileges are reviewed quarterly.
- **Termination:** Upon separation (voluntary or involuntary), all access is revoked within **1 hour**. This includes cloud accounts, VPN, email, code repositories, and any shared credentials (which are rotated).
- **Privileged Access:** Administrative access is granted on a time-limited, just-in-time basis where feasible.

#### Authentication Standards
- Minimum password length: 14 characters.
- Passwords checked against known-breach databases (e.g., HIBP) at creation and periodically.
- Account lockout after 5 failed attempts (progressive backoff, not permanent lockout to avoid DoS).

---

## 7. AI-Specific Data Handling

This section addresses the unique risks and controls associated with using Anthropic's Claude API to process customer tax information. **This is the section that makes this WISP different from a generic template.**

### 7.1 System Architecture — Data Flow

The following describes how customer data flows through the AI-Tax system:

```
┌──────────────┐     TLS 1.2+     ┌──────────────────┐
│   Customer   │ ──────────────── │   AI-Tax Web App  │
│   Browser    │   (uploads W-2,  │   (Application    │
│              │    enters data)  │    Server)        │
└──────────────┘                  └────────┬─────────┘
                                           │
                                    ┌──────┴──────┐
                                    │             │
                              ┌─────▼─────┐ ┌────▼────────────┐
                              │  AI-Tax   │ │  AI-Tax         │
                              │  Database │ │  Processing     │
                              │  (Encrypted│ │  Service        │
                              │  at rest) │ │                 │
                              └───────────┘ └────┬────────────┘
                                                  │
                                           TLS 1.2+  
                                           (API call)
                                                  │
                                           ┌──────▼──────┐
                                           │  Anthropic  │
                                           │  Claude API │
                                           │  (Stateless)│
                                           └─────────────┘
```

**Key data flow principles:**

1. **Customer uploads** tax documents (W-2, 1099, etc.) via encrypted HTTPS connection.
2. Documents are **parsed locally first** — OCR and field extraction happen on our infrastructure where possible, to minimize data sent to the API.
3. **Only necessary data** is sent to the Claude API. We do **not** send raw document images to the API unless required for parsing. When possible, we send extracted structured data.
4. **SSN handling:** Full SSNs are **never** sent to the Claude API unless strictly required for a specific tax calculation. When SSNs must be referenced, we use tokenized or truncated identifiers (last 4 digits) in API prompts.
5. **API responses** are processed server-side, validated, and stored in our encrypted database.
6. **No customer data** is cached in the API layer beyond the duration of a single request/response cycle.

### 7.2 Anthropic API — Data Protection Guarantees

[COMPANY NAME] uses the **Anthropic API** (commercial tier) which provides the following contractual protections:

| Protection | Detail |
|---|---|
| **No model training on inputs** | Anthropic's API Terms of Service (commercial) state that customer inputs and outputs are **not used to train models**. This is contractually binding. |
| **Data retention** | Anthropic retains API inputs/outputs for up to **30 days** for trust and safety purposes, then deletes them. With a zero-retention agreement (if obtained), this period may be reduced. |
| **No human review** (default) | API inputs are not reviewed by Anthropic employees unless flagged for trust & safety, or required by law. |
| **SOC 2 Type II** | Anthropic maintains SOC 2 Type II compliance for the API infrastructure. |
| **Encryption in transit** | All API communication is encrypted via TLS 1.2+. |

**Action items:**
- [ ] Execute Anthropic's **Data Processing Agreement (DPA)** if available.
- [ ] Request **zero-data-retention** agreement for API calls containing customer tax information.
- [ ] Obtain and review Anthropic's latest **SOC 2 Type II report** annually.

### 7.3 Prompt Security & Injection Prevention

AI systems introduce a unique attack vector: **prompt injection** — where malicious content in user-uploaded documents could manipulate the AI's behavior.

**Controls:**

1. **Input Sanitization:** All user-provided content (including OCR output from uploaded documents) is sanitized before inclusion in API prompts. Special characters and instruction-like patterns are escaped or flagged.
2. **System Prompt Hardening:** System prompts explicitly instruct the model to:
   - Only process tax-related calculations.
   - Never output raw SSNs, bank account numbers, or other PII in responses unless specifically requested by the application (not the user-input portion of the prompt).
   - Ignore instructions embedded in user-uploaded documents.
3. **Output Validation:** API responses are validated against expected schemas. Unexpected outputs (e.g., responses containing SSNs when none should be present, or instructions to redirect data) are flagged and blocked.
4. **Prompt/Response Logging:** All API prompts and responses are logged (with PII redacted in logs) for audit and anomaly detection. Logs are reviewed for signs of injection attempts.
5. **Role Separation in Prompts:** We use structured prompt formats that clearly delineate system instructions from user data, reducing the surface area for injection attacks.

### 7.4 AI Output Review & Tax Accuracy

Because AI-Tax generates tax calculations that have legal and financial consequences:

1. **All AI-generated tax calculations** are validated against deterministic tax computation logic before being presented to the user. The AI assists with document parsing and user guidance — it does not have unsupervised authority to file tax returns.
2. **Users review and confirm** all tax return data before filing. A clear disclosure states that AI was used to assist in preparation.
3. **Audit trail:** Every AI-generated value is logged with the prompt that produced it, enabling post-hoc review.
4. **Confidence thresholds:** When the AI's confidence in a parsed value is below a configurable threshold, the user is prompted to manually verify the field.

### 7.5 Data Minimization for API Calls

- **Principle:** Send the minimum data necessary to the Claude API for each task.
- **Implementation:**
  - Tax document parsing: Send extracted text fields, not raw images (when possible).
  - Tax calculations: Send anonymized or tokenized data; replace SSNs with placeholders.
  - User Q&A: Send only the specific question and relevant context, not the user's entire tax profile.
- **Prohibited:** Never send the following to the API in a single prompt: full SSN + full name + date of birth + bank account number. If multiple sensitive fields are needed, they must be split across separate, unlinkable API calls or tokenized.

---

## 8. Employee Training & Awareness

### 8.1 Requirements

All personnel (employees, contractors, interns) with access to customer information or systems that process it must complete security training:

| Training | Frequency | Audience |
|---|---|---|
| **Security Awareness (General)** | Upon hire + annually | All personnel |
| **Phishing Simulation** | Quarterly | All personnel |
| **Tax Data Handling** | Upon hire + annually | All personnel with data access |
| **Secure Development (OWASP, AI Security)** | Upon hire + annually | Engineering team |
| **Incident Response** | Upon hire + annually (+ tabletop exercise) | Incident response team |
| **IRS Pub 4557 Compliance** | Annually (before tax season) | All personnel |

### 8.2 Training Content

Training must cover, at minimum:

- This WISP and its requirements
- Recognizing and reporting phishing and social engineering
- Proper handling of SSNs, bank information, and tax documents
- Rules for remote work (VPN, screen lock, no public Wi-Fi without VPN)
- Password hygiene and MFA usage
- AI-specific risks: prompt injection, data leakage through AI outputs, over-reliance on AI results
- Incident reporting procedures
- Regulatory obligations (GLBA, FTC Safeguards, IRS requirements)
- Consequences of non-compliance (up to termination and legal liability)

### 8.3 Documentation

- Training completion is documented with date, content covered, and attendee acknowledgment.
- Records are maintained for a minimum of **3 years**.
- Personnel who fail to complete required training within **30 days** of the due date will have system access suspended until training is completed.

### 8.4 Responsible Party

| Role | Person |
|---|---|
| Training Program Owner | [SECURITY COORDINATOR NAME] |
| Training Content Developer | [TRAINING LEAD or external vendor] |
| Completion Tracking | [HR CONTACT or SECURITY COORDINATOR NAME] |

---

## 9. Incident Response Plan

### 9.1 Objective

Detect, contain, eradicate, and recover from security events affecting customer information with minimal impact, and meet all legal notification obligations.

### 9.2 Incident Response Team

| Role | Name | Contact |
|---|---|---|
| **Incident Commander** | [SECURITY COORDINATOR NAME] | [PHONE / EMAIL] |
| **Technical Lead** | [ENGINEERING LEAD] | [PHONE / EMAIL] |
| **Communications Lead** | [CEO or COMMS PERSON] | [PHONE / EMAIL] |
| **Legal Counsel** | [LEGAL CONTACT or OUTSIDE COUNSEL] | [PHONE / EMAIL] |
| **External Forensics** (on retainer) | [FORENSICS FIRM, if applicable] | [PHONE / EMAIL] |

### 9.3 Incident Classification

| Severity | Description | Examples | Response Time |
|---|---|---|---|
| **Critical (P1)** | Confirmed breach of customer PII/FTI | Database exfiltration, ransomware with data theft | Immediate (within 1 hour) |
| **High (P2)** | Active attack or high-probability breach | Brute-force attack in progress, compromised employee credentials | Within 4 hours |
| **Medium (P3)** | Suspicious activity, potential vulnerability exploitation | Unusual API access patterns, prompt injection attempts | Within 24 hours |
| **Low (P4)** | Minor policy violation, false positive | Employee accessing a system without proper authorization (no data accessed) | Within 72 hours |

### 9.4 Response Phases

#### Phase 1: Detection & Analysis
- **Sources:** Automated alerts (SIEM, WAF, EDR), employee reports, customer reports, third-party notifications.
- **Triage:** The Incident Commander assesses scope, affected data, and classifies severity.
- **Evidence Preservation:** Immediately capture logs, system snapshots, and memory dumps. Preserve chain of custody.
- **Documentation:** Open an incident ticket with timestamp, reporter, initial assessment, and all actions taken.

#### Phase 2: Containment
- **Short-term:** Isolate affected systems (revoke compromised credentials, block malicious IPs, disable compromised API keys). For Claude API-related incidents, rotate API keys immediately.
- **Long-term:** Implement temporary controls to prevent spread while maintaining essential services.
- **Decision point:** If customer data is confirmed compromised, proceed immediately to Phase 4 (Notification) in parallel with continued containment.

#### Phase 3: Eradication & Recovery
- Remove the root cause (patch vulnerability, remove malware, close unauthorized access).
- Restore systems from known-good backups if integrity is in question.
- Verify restoration through integrity checks and testing.
- Monitor closely for re-occurrence (elevated monitoring for 30 days post-incident).

#### Phase 4: Notification

##### Federal Notifications

| Agency | Trigger | Timing | Method |
|---|---|---|---|
| **IRS** (Report to TIGTA) | Any theft of taxpayer data, any data breach involving tax information | Immediately | Call TIGTA at 1-800-366-4484; file online at www.treasury.gov/tigta |
| **FTC** | Breach affecting 500+ consumers (per Health Breach Notification Rule, if applicable) or as required | As applicable | ftc.gov/enforcement |
| **FBI / IC3** | Cyber intrusion, ransomware | Recommended for all P1/P2 | ic3.gov |

##### State Notifications

- **All 50 states** (plus DC, territories) have breach notification laws with varying thresholds and timelines.
- **General rule:** Notify affected individuals **without unreasonable delay**, typically within **30–60 days** of discovery (some states require as few as 30 days; follow the strictest applicable deadline).
- **State Attorneys General:** Many states require AG notification (often when breach affects >500 state residents). The Security Coordinator maintains a **state notification matrix** as a separate working document.
- **Consumer Reporting Agencies:** If breach affects >5,000 individuals in a single state, notify major consumer reporting agencies (Equifax, Experian, TransUnion).

##### Customer Notification

- Notification to affected individuals must include:
  - Description of what happened and dates
  - Types of information involved
  - Steps taken in response
  - What individuals can do to protect themselves
  - Contact information for questions
  - Information about free credit monitoring (provided for 12–24 months for tax data breaches)
- Notification method: Written notice (postal mail) + email if address on file. Substitute notice if contact info is insufficient.

#### Phase 5: Post-Incident Review
- Conduct a **blameless post-mortem** within 14 days of incident closure.
- Document: root cause, timeline, what worked, what didn't, and remediation actions.
- Update this WISP and the Risk Register based on lessons learned.
- Report to the Board/CEO.

### 9.5 IRS-Specific Reporting

Per IRS Publication 4557, tax professionals who experience a data breach must also:

1. Contact their **local IRS Stakeholder Liaison** to report the breach.
2. File **Form 14039** (Identity Theft Affidavit) for affected clients.
3. File an **identity theft report** with local law enforcement.
4. Contact the **IRS Identity Protection Specialized Unit** at 1-800-908-4490.

---

## 10. Service Provider Oversight

### 10.1 Requirement

Pursuant to 16 CFR § 314.4(f), [COMPANY NAME] selects and retains service providers capable of maintaining appropriate safeguards for customer information, and contractually requires them to implement and maintain such safeguards.

### 10.2 Current Service Providers

| Provider | Service | Data Exposure | Risk Level | Contract Status |
|---|---|---|---|---|
| **Anthropic** | Claude API (tax document parsing, calculations, user Q&A) | Customer data in API prompts (minimized per §7.5) | High | [API Terms of Service / DPA — Status] |
| **[CLOUD PROVIDER]** | Infrastructure hosting (compute, storage, database) | All customer data (encrypted) | High | [Contract / BAA Status] |
| **[IRS E-FILE PROVIDER]** | Electronic tax filing submission | Tax return data, SSN, income | Critical | [Agreement Status] |
| **[PAYMENT PROCESSOR]** | Payment processing | Payment card or bank info (PCI DSS scope) | High | [PCI DSS Certified — Status] |
| **[EMAIL PROVIDER]** | Transactional email | Email addresses, names | Medium | [DPA Status] |
| **[MONITORING/SIEM]** | Security monitoring, log management | Log data (PII redacted) | Medium | [Contract Status] |
| **[OCR SERVICE, if external]** | Document text extraction | Uploaded document content | High | [DPA Status] |

### 10.3 Due Diligence

Before engaging any service provider with access to customer information, [COMPANY NAME] will:

1. **Assess** the provider's security posture (SOC 2 report, ISO 27001 certification, penetration test results, or security questionnaire).
2. **Verify** compliance certifications relevant to the service (e.g., PCI DSS for payment, SOC 2 for cloud/API).
3. **Contractually require** the provider to:
   - Implement and maintain safeguards appropriate to the sensitivity of the data.
   - Promptly notify [COMPANY NAME] of any security event affecting our data (within 24–72 hours).
   - Cooperate with incident investigation and forensics.
   - Delete or return customer data upon contract termination.
   - Not use customer data for any purpose other than providing the contracted service (including no model training — specifically relevant for Anthropic).
4. **Document** the due diligence process and maintain records.

### 10.4 Ongoing Monitoring

- **Annually:** Review each provider's security posture (updated SOC 2 reports, certifications, or re-assessment).
- **Continuously:** Monitor for provider security incidents via news, vendor advisories, and threat intelligence feeds.
- **Contractual right to audit:** Where feasible, retain the right to audit or request evidence of compliance.
- **Termination:** If a provider fails to maintain adequate safeguards and cannot remediate promptly, [COMPANY NAME] will transition to an alternative provider.

---

## 11. Data Retention & Destruction Policy

### 11.1 Retention Schedule

| Data Type | Retention Period | Basis |
|---|---|---|
| **Tax returns (as filed)** | 3 years from filing date | IRS standard statute of limitations; consistent with customer-facing policies |
| **Tax preparation workpapers** | 3 years from filing date | Aligned with filed return retention |
| **Uploaded source documents** (W-2, 1099 images) | 3 years from filing date, or end of engagement + 1 year, whichever is longer | Business need; shorter than returns because originals are with the client |
| **Customer account data** (name, email, phone) | Duration of account + 3 years after closure | Business need + statute of limitations |
| **SSNs** | Same as tax return retention (3 years) | Required for tax prep; destroyed with associated return |
| **Bank account / routing numbers** | Only until refund is confirmed deposited, then deleted. Maximum 120 days. | Data minimization — no need to retain after use |
| **Claude API call logs** (prompts/responses) | 90 days (with PII redacted) for debugging; PII-containing originals deleted within 30 days | Operational need balanced against data minimization |
| **Application access logs** | 1 year | Security monitoring and audit |
| **Security event logs** | 3 years | Incident investigation and compliance |
| **Employee training records** | 3 years after separation | Compliance documentation |

### 11.2 Destruction Methods

| Data Format | Destruction Method |
|---|---|
| **Electronic data (databases, files)** | Cryptographic erasure (destroy encryption keys) or NIST SP 800-88 compliant secure deletion |
| **Cloud storage objects** | Deletion via cloud provider API + verification that object is no longer retrievable. For encrypted data, key destruction is sufficient. |
| **Backup media** | Encrypted backups: destroy encryption keys. Unencrypted (should not exist): overwrite per NIST SP 800-88 |
| **Employee devices** (upon separation) | Factory reset + cryptographic erasure of disk encryption keys |
| **Paper documents** (if any exist) | Cross-cut shredding (P-4 or higher security level) |

### 11.3 Destruction Procedures

1. **Automated:** Data past its retention period is identified and queued for destruction by automated processes running [weekly/monthly].
2. **Manual review:** Before bulk destruction, the Security Coordinator reviews the destruction queue to prevent premature deletion (e.g., data under legal hold).
3. **Legal hold:** If litigation, regulatory investigation, or audit is pending or anticipated, all relevant data is preserved regardless of retention schedule until the hold is lifted by Legal Counsel.
4. **Certification:** Destruction of customer data is documented with date, data type, method, and person responsible. Certificates of destruction are maintained for 3 years.

### 11.4 Customer-Initiated Deletion

- Customers may request deletion of their data by contacting [SUPPORT EMAIL / in-app request].
- Upon verified request, all customer data not subject to legal or regulatory retention requirements is deleted within **30 days**.
- The customer is notified upon completion. Data retained for regulatory reasons (e.g., filed tax return copies) is disclosed to the customer along with the retention period.

---

## 12. Physical & Logical Security

### 12.1 Physical Security

AI-Tax operates as a cloud-native application. [COMPANY NAME] does not maintain physical data centers or on-premises servers that store customer information.

**Office / Remote Work Controls:**

- **Clean Desk Policy:** No customer information (paper or on-screen) is left visible when unattended.
- **Screen Lock:** All devices auto-lock after 5 minutes of inactivity.
- **Full-Disk Encryption:** All employee laptops and workstations use full-disk encryption (FileVault for macOS, BitLocker for Windows, LUKS for Linux).
- **Secure Disposal:** Devices are securely wiped before disposal or reuse (see §11.2).
- **No Local Storage:** Customer data must not be stored on employee local devices. All work is performed on centrally managed, cloud-hosted systems.
- **Visitors:** [If office exists:] Visitors are escorted at all times. No visitor access to systems or workstations.

### 12.2 Logical Security (Cloud Infrastructure)

- **Identity & Access Management (IAM):** Cloud provider IAM with MFA enforced for all human users. Service accounts use short-lived credentials.
- **Infrastructure as Code (IaC):** All infrastructure is defined in code (e.g., Terraform, CloudFormation), version-controlled, and peer-reviewed before deployment. No manual configuration of production systems.
- **Secrets Management:** All secrets (API keys, database credentials, encryption keys) are stored in a dedicated secrets manager — never in source code, environment variables in plaintext, or configuration files.
- **Container / Compute Hardening:**
  - Minimal base images (distroless or Alpine).
  - Non-root execution.
  - Read-only file systems where possible.
  - No SSH access to production containers; debugging via secure, audited channels only.
- **Public Access Prevention:**
  - S3 buckets (or equivalent) are private by default. Public access is explicitly blocked at the account level.
  - Database ports are never exposed to the public internet.
  - Admin interfaces are accessible only via VPN or private network.

---

## 13. Testing & Monitoring

### 13.1 Vulnerability Management & Penetration Testing

| Activity | Frequency | Scope | Responsible |
|---|---|---|---|
| **Automated vulnerability scanning** | Weekly (infrastructure) + on every deployment (application) | All production systems and application code | Engineering team |
| **Dependency scanning** | On every build + daily automated scan | All third-party libraries and packages | Engineering team (automated) |
| **Penetration testing** | Annually (external firm) + after significant architecture changes | Full application + API + infrastructure | External firm + Security Coordinator |
| **AI-specific testing** | Annually + before major prompt changes | Prompt injection, data leakage, output manipulation | Engineering + Security Coordinator |
| **Cloud configuration review** | Quarterly (automated) + annually (manual) | IAM, network, storage, encryption settings | Security Coordinator |

**Findings:**

- Critical and High severity findings are remediated within **15 days**.
- Medium findings within **30 days**.
- Low findings within **90 days**.
- All findings are tracked in the Risk Register with owner, status, and target date.

### 13.2 Continuous Monitoring

| Monitoring Type | Tool Category | What's Monitored |
|---|---|---|
| **Security Information & Event Management (SIEM)** | [SIEM TOOL, e.g., Datadog, Splunk, AWS Security Hub] | Aggregated security logs, correlation rules, alerts |
| **Intrusion Detection** | WAF + cloud-native threat detection (e.g., GuardDuty) | Network anomalies, known-bad IPs, API abuse |
| **Application Performance Monitoring** | [APM TOOL] | Application errors, latency spikes, unusual API patterns |
| **API Monitoring** | Custom + APM | Claude API call patterns, response anomalies, error rates, prompt injection indicators |
| **Database Monitoring** | Cloud-native + database audit logs | Query patterns, failed authentication, bulk data access |
| **Uptime Monitoring** | [MONITORING TOOL] | Availability of all customer-facing services |

### 13.3 Audit Logging

The following events are logged with timestamp, user/service identity, source IP, action, and outcome:

- All authentication events (success and failure)
- All access to customer information (read, write, delete)
- All administrative actions (IAM changes, configuration changes)
- All API calls to Anthropic Claude (with PII redacted)
- All data export or download operations
- All changes to security configurations
- All access to encryption keys

**Log Protection:**

- Logs are stored in a dedicated, append-only log store.
- Log access is restricted to the Security Coordinator and authorized security personnel.
- Logs are retained per the schedule in §11.1.
- Log integrity is protected via checksums or tamper-evident logging.
- Logs are **never** stored with unredacted customer PII (SSN, bank account numbers). A lookup table connects log identifiers to customer records when investigation requires it.

### 13.4 Annual Security Review

At minimum annually, the Security Coordinator will:

1. Review and update this WISP.
2. Review the Risk Assessment (§5) and update risk scores based on new threats and incidents.
3. Review access controls — confirm all active accounts are still needed and appropriately permissioned.
4. Review service provider compliance (§10).
5. Review incident response readiness — conduct a tabletop exercise.
6. Review penetration testing and vulnerability scanning results.
7. Prepare a written report to the Board/CEO summarizing the security program's effectiveness.
8. Update the effective date and version of this document.

---

## 14. Policy Governance

### 14.1 Amendments

This WISP may be amended by the Security Coordinator with approval from [CEO / BOARD]. Material changes are communicated to all personnel within **30 days**.

### 14.2 Exceptions

Any exception to this WISP must be:

1. Documented in writing with a clear business justification.
2. Approved by the Security Coordinator and the CEO.
3. Time-limited (maximum 6 months, renewable with re-justification).
4. Accompanied by compensating controls.
5. Logged in the Risk Register.

### 14.3 Enforcement

Violations of this WISP may result in disciplinary action up to and including termination of employment or contract. Depending on the nature and severity of the violation, legal action may be pursued.

### 14.4 Related Documents

| Document | Description |
|---|---|
| Risk Register | Working document tracking all identified risks and treatments |
| Incident Response Runbook | Detailed, step-by-step playbook for security incidents |
| State Notification Matrix | Breach notification requirements by state |
| Service Provider Register | Detailed vendor security assessments |
| Data Flow Diagrams | Technical architecture and data flow documentation |
| Privacy Policy | Customer-facing privacy disclosures |
| Employee Security Agreement | Signed acknowledgment of security responsibilities |

---

## 15. Signature Page

By signing below, the undersigned acknowledges that they have reviewed this Written Information Security Plan, understand its requirements, and commit to its implementation.

<br>

**Security Coordinator:**

| | |
|---|---|
| Name | [SECURITY COORDINATOR NAME] |
| Title | [TITLE] |
| Signature | ________________________________ |
| Date | ________________________________ |

<br>

**Chief Executive Officer:**

| | |
|---|---|
| Name | [CEO NAME] |
| Title | CEO |
| Signature | ________________________________ |
| Date | ________________________________ |

<br>

**Acknowledgment — All Personnel:**

Each employee and contractor with access to customer information must sign a separate acknowledgment form confirming they have read, understand, and will comply with this WISP. Signed forms are maintained by [HR CONTACT / SECURITY COORDINATOR NAME].

---

## Appendix A: Quick-Reference Compliance Checklist

Use this checklist for annual review:

- [ ] Security Coordinator designated and current (§3)
- [ ] Risk assessment completed within past 12 months (§5)
- [ ] Firewall / network security rules reviewed (§6.1)
- [ ] MFA enforced on all systems with customer data (§6.2)
- [ ] Encryption at rest and in transit verified (§6.3)
- [ ] Anti-malware / EDR current on all endpoints (§6.4)
- [ ] Backups tested — successful restore within past 90 days (§6.5)
- [ ] Access control review completed — no unnecessary access (§6.6)
- [ ] Anthropic DPA / data handling agreement current (§7.2)
- [ ] Prompt injection controls tested (§7.3)
- [ ] AI output validation functioning correctly (§7.4)
- [ ] All personnel training current (§8)
- [ ] Incident response tabletop exercise conducted (§9)
- [ ] Service provider SOC 2 / security reviews current (§10)
- [ ] Data destruction executed for expired data (§11)
- [ ] Penetration test completed within past 12 months (§13.1)
- [ ] SIEM / monitoring alerts reviewed and tuned (§13.2)
- [ ] Audit logs reviewed for anomalies (§13.3)
- [ ] Written report delivered to Board/CEO (§13.4)
- [ ] This WISP reviewed and updated (§14)

---

## Appendix B: IRS Publication 4557 Crosswalk

| IRS Pub 4557 Requirement | WISP Section |
|---|---|
| Designate a security coordinator | §3 |
| Risk assessment | §5 |
| Firewall | §6.1 |
| Multi-factor authentication | §6.2 |
| Encryption | §6.3 |
| Anti-virus / anti-malware | §6.4 |
| Backup software | §6.5 |
| Access control | §6.6 |
| Employee training | §8 |
| Data theft response plan | §9 |
| Report data theft | §9.4, §9.5 |
| Secure disposal of data | §11 |
| Monitor physical security | §12 |
| Vet third-party providers | §10 |
| Create and maintain a WISP | This document |

---

## Appendix C: FTC Safeguards Rule (16 CFR Part 314) Crosswalk

| FTC Requirement | Citation | WISP Section |
|---|---|---|
| Qualified individual to oversee program | §314.4(a) | §3 |
| Written risk assessment | §314.4(b) | §5 |
| Design and implement safeguards | §314.4(c) | §6, §7, §12 |
| Regularly test safeguards | §314.4(d) | §13 |
| Train security personnel | §314.4(e) | §8 |
| Oversee service providers | §314.4(f) | §10 |
| Evaluate and adjust program | §314.4(g) | §13.4, §14 |
| Incident response plan | §314.4(h) | §9 |
| Board reporting | §314.4(i) | §3.2 (item 6) |
| Encryption of customer information in transit + at rest | §314.4(c)(3) | §6.3 |
| MFA for any individual accessing customer information | §314.4(c)(5) | §6.2 |
| Data retention limitations | §314.4(c)(6) | §11 |
| Change management | §314.4(c)(8) | §12.2 (IaC), §14 |
| Access controls | §314.4(c)(1) | §6.6 |
| System and network monitoring | §314.4(c)(2) | §13.2 |

---

*This document is confidential and intended for internal use by [COMPANY NAME] and its authorized personnel only. Distribution outside the organization requires the Security Coordinator's written approval.*

*© [YEAR] [COMPANY NAME]. All rights reserved.*
