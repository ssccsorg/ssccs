# Securing Intellectual Property with C2PA and Verifiable Provenance

## Executive Summary

This report provides a comprehensive technical strategy for securing intellectual property (IP) using the Coalition for Content Provenance and Authenticity (C2PA) standard, along with cross‑verification mechanisms and alternative provenance solutions. The current test‑certificate implementation is evaluated, and a roadmap toward production‑grade C2PA deployment is outlined. The strategy emphasizes cryptographic binding of IP to its digital representation, verifiable timestamps, and integration with existing PDF‑signing workflows.



## 1. Current Implementation Analysis

The existing Python script (`sign_c2pa.py`) demonstrates the core C2PA workflow: generating a SHA‑256 hash of the target PDF, injecting it as a custom assertion (`org.ssccs.pdfhash`), and using `c2patool` to produce a sidecar `.c2pa` manifest. The current approach uses a **test certificate** with no valid trust chain, which means:

- The manifest signature is mathematically valid but **untrusted** by standard C2PA validators.
- Verification tools (e.g., Adobe Inspect) will show “untrusted” or “unrecognized” because the certificate does not chain to a root in the C2PA Trust List.
- No trusted timestamp is included, causing the manifest to become invalid upon certificate expiry.

### 1.1 Production Readiness Gap

For the C2PA signatures to be **trusted** in production, three components are required:

1. A **publicly trusted certificate** from a C2PA‑conformant Certificate Authority (CA).
2. A **Trusted Timestamp Authority (TSA)** token proving the signature existed at a specific time.
3. Optional but recommended: a **Key Management Service (KMS)** or Hardware Security Module (HSM) to protect the private key.



## 2. C2PA Technical Architecture

### 2.1 Core Components

C2PA is an open, royalty‑free technical specification published under the Joint Development Foundation, currently at **v2.3 (December 2025)**. The coalition includes Adobe, Microsoft, Google, Intel, Arm, BBC, Sony, and Truepic.

A C2PA manifest is the core data structure – a digitally signed record embedded inside a media file (or stored as a sidecar `.c2pa` file) that documents the content’s origin, creation tools, and complete edit history. Every manifest has a three‑layer hierarchy:

| Component | Description |
|---|---|
| **Assertions** | Individual statements made by the signer about the asset (e.g., “captured by device X”, “AI was used in creation”, custom claims like `org.ssccs.pdfhash`). |
| **Claim** | The signed container that groups assertions into a single, tamper‑evident data structure. |
| **Claim Signature** | Cryptographic proof binding the claim to the signer’s identity, created using the signer’s private key. |

All assertions are optional by specification – a valid manifest can make very few actual claims.

### 2.2 Manifest Storage Options

A manifest store can be:
- **Embedded** directly in the asset’s metadata (supported for JPEG, PNG, MP4, PDF, WebP, AVIF).
- **Sidecar file** (`.c2pa` extension) – recommended for formats where embedding is impractical or for keeping original files unchanged.
- **Remote manifest** – linked from the asset’s metadata, allowing large manifests to be stored externally.

### 2.3 Trust Infrastructure

The **C2PA Trust List** is a publicly maintained list of Certificate Authorities (CAs) whose certificates have been certified under the C2PA Conformance Programme for signing Content Credentials. Validators must check three things: Trust List membership, revocation status via CRL or OCSP, and the full certificate chain – not just the signature.

The **Interim Trust List (ITL)** , used during C2PA’s early adoption phase from 2021 through 2025, was frozen on January 1, 2026. As of early 2026, confirmed conformant CAs include **DigiCert** and **SSL.com** (which joined in September 2025).



## 3. Alternative and Complementary Solutions

To achieve a robust IP protection strategy, C2PA should be used alongside complementary technologies that provide independent verification and redundancy.

### 3.1 Traditional PKI + PDF Signatures

**Public Key Infrastructure (PKI)** provides a mature, legally recognized framework for document signing. PDF Advanced Electronic Signatures (PAdES) enable embedding certificate chains, timestamps, and validation data for long‑term validation (LTV), ensuring signed files remain legally valid years later.

| Feature | C2PA | PKI + PAdES |
|---|---|---|
| Binding to content | Hard binding via JUMBF, cryptographic hash | Embedded signature dictionary |
| Timestamp support | RFC 3161 recommended | RFC 3161 standard |
| Trust model | C2PA Trust List (CA‑based) | Standard PKI (WebTrust, eIDAS) |
| Legal recognition | Emerging | Mature (eIDAS, ESIGN) |

**Cross‑verification benefit:** PKI signatures provide an independent, legally admissible proof of authorship that can be verified without C2PA‑specific tooling.

### 3.2 IETF SCITT (Supply Chain Integrity, Transparency, and Trust)

SCITT is an IETF‑standardized architecture for transparency services. It defines a generic, interoperable, and scalable architecture to enable transparency across any supply chain with minimum adoption barriers.

Issuers register Signed Statements on any Transparency Service, receiving receipts that prove inclusion in an append‑only log. Relying Parties can verify these statements without trusting the issuer.

**SCITT vs. C2PA:** SCITT focuses on **transparency services** (public, auditable logs) rather than asset‑bound manifests. It can complement C2PA by providing an independent, publicly verifiable record that a given document existed with a specific hash at a specific time.

### 3.3 OpenTimestamps (OTS)

OpenTimestamps provides **trustless timestamping** using the Bitcoin blockchain:

- **No trusted third party** – unlike TSA, you don’t need to trust a certificate authority.
- **Quantum‑resistant** – hash functions remain secure against quantum computers.
- **Permanent** – proofs last as long as the Bitcoin blockchain exists.
- **Verifiable** – anyone can independently verify timestamps.

Calendars aggregate hashes into a Merkle tree, the root hash is embedded in a Bitcoin transaction, and the Bitcoin network confirms the timestamp. Anyone can later verify the timestamp against the blockchain.

**Use case:** OTS can provide an independent, trustless timestamp for the PDF hash that does not rely on any CA or TSA, serving as a **cryptographic notary** for the document’s existence.

### 3.4 W3C Verifiable Credentials (VCs)

W3C Verifiable Credentials Data Integrity 1.1 provides a framework to associate proofs of integrity with credentials, using JSON Object Signing and Encryption (JOSE) or other cryptographic suites. VCs support decentralized identifiers (DIDs) and can be used to assert claims about digital assets without relying on a central registry.

**Cross‑verification benefit:** VCs can be used to issue a verifiable credential that asserts “Organization X claims that document hash Y is their IP,” independent of C2PA’s trust infrastructure.

### 3.5 KERI (Key Event Receipt Infrastructure)

KERI is a decentralized identifier protocol that operates without mandatory dependence on distributed ledgers. It provides self‑certifying identifiers and key event logs (KELs) that allow verification without contacting a central authority.

**Use case:** KERI can establish a persistent, decentralized identity for the organization that signs manifests, providing an alternative trust anchor that does not rely on traditional CAs.



## 4. Cross‑Verification Strategy

A robust IP protection system must not rely on a single trust mechanism. The following cross‑verification matrix outlines how multiple technologies can be combined:

| Technology | Proof Provided | Independent Verification Method |
|---|---|---|
| C2PA manifest | Asset provenance, editing history, signature identity | Verify via `c2patool`, Adobe Inspect, or any C2PA‑compatible validator |
| PKI digital signature (PAdES) | Author identity, document integrity, legal timestamp | Standard PDF readers, certificate chain validation, TSA verification |
| SCITT transparency receipt | Public, append‑only record of statement | Query any SCITT‑compliant Transparency Service |
| OpenTimestamps | Trustless, blockchain‑anchored timestamp | Verify against Bitcoin blockchain independently |
| W3C Verifiable Credential | Decentralized claim about the asset | Verify DID document and signature independently |

**Recommended verification pipeline:**
1. Extract the PDF hash from the C2PA manifest (custom `org.ssccs.pdfhash` assertion).
2. Verify the C2PA manifest signature against the C2PA Trust List.
3. Verify the PDF’s embedded PKI signature (if present) using standard PKI validation.
4. Query the SCITT Transparency Service for a receipt matching the PDF hash.
5. Verify the OpenTimestamps proof against the Bitcoin blockchain.
6. Check if a W3C VC asserting the same hash exists and is signed by the organization’s DID.

If any two independent methods agree on the same hash and timestamp, the provenance claim is strongly corroborated.



## 5. Practical Implementation Tasks

The following tasks represent a phased migration from the test‑certificate prototype to a production‑grade, cross‑verified IP protection system.

### Task 1: Acquire Production C2PA Signing Certificate

| Action | Details |
|---|---|
| **Objective** | Replace test certificate with a publicly trusted C2PA‑conformant certificate. |
| **Steps** | 1. Identify C2PA‑conformant CA (DigiCert, SSL.com, or future entrants).<br>2. Complete CA’s identity verification process.<br>3. Obtain PKCS#12 (.pfx) container with certificate chain and private key.<br>4. Verify that the certificate chains to a root in the C2PA Trust List. |
| **Dependencies** | C2PA Conformance Programme enrollment of selected CA. |
| **Output** | Production signing certificate ready for integration. |

### Task 2: Integrate RFC 3161 Trusted Timestamping

| Action | Details |
|---|---|
| **Objective** | Add trusted timestamps to C2PA manifests to preserve validity beyond certificate expiry. |
| **Steps** | 1. Select a TSA (e.g., DigiCert TSA, SSL.com TSA, or free public TSA for testing).<br>2. Modify `sign_c2pa.py` to request an RFC 3161 timestamp token during signing.<br>3. Integrate the timestamp token into the C2PA claim signature. |
| **Dependencies** | TSA service availability. |
| **Output** | C2PA manifests with trusted timestamps; verification tools will show “timestamped at [time].” |

### Task 3: Transition to Production Key Management

| Action | Details |
|---|---|
| **Objective** | Secure private key using KMS or HSM instead of filesystem storage. |
| **Steps** | 1. Evaluate cloud KMS (AWS KMS, Azure Key Vault, Google Cloud KMS) or on‑premise HSM.<br>2. Implement external signer interface (C2PA tool supports external signers via API).<br>3. Migrate signing operations to use KMS/HSM for private key operations. |
| **Dependencies** | KMS/HSM procurement and integration. |
| **Output** | Private key never leaves secure hardware; signing requests are forwarded to KMS. |

### Task 4: Implement PKI PDF Signing (PAdES)

| Action | Details |
|---|---|
| **Objective** | Add standard PKI digital signatures to PDFs for independent verification. |
| **Steps** | 1. Use a PDF signing library (e.g., PyPDF2 with cryptography, or commercial SDK).<br>2. Embed the C2PA sidecar reference in the PDF’s metadata.<br>3. Apply PAdES signature with the same certificate or a separate document‑signing certificate.<br>4. Include RFC 3161 timestamp in the PDF signature. |
| **Dependencies** | PDF signing library, TSA integration. |
| **Output** | PDFs containing both C2PA sidecar manifests and embedded PKI signatures. |

### Task 5: Implement OpenTimestamps Integration

| Action | Details |
|---|---|
| **Objective** | Create trustless, blockchain‑anchored timestamps for PDF hashes. |
| **Steps** | 1. Use Python OpenTimestamps client or `opentimestamps` CLI.<br>2. Submit the PDF’s SHA‑256 hash to public OpenTimestamps calendars.<br>3. Save the `.ots` proof file alongside the PDF.<br>4. Modify the build system to generate OTS proofs automatically. |
| **Dependencies** | OpenTimestamps client, Bitcoin blockchain access. |
| **Output** | `.ots` file for each PDF, verifiable against Bitcoin blockchain independently. |

### Task 6: Deploy SCITT Transparency Service Integration

| Action | Details |
|---|---|
| **Objective** | Register signed statements about each PDF in a public transparency log. |
| **Steps** | 1. Deploy or subscribe to a SCITT‑compliant Transparency Service.<br>2. For each PDF, issue a Signed Statement containing the PDF hash and metadata.<br>3. Register the statement with the Transparency Service.<br>4. Store the returned receipt (proof of inclusion). |
| **Dependencies** | SCITT service availability (e.g., DataTrails, Microsoft SCITT). |
| **Output** | Verifiable receipts proving that the PDF’s provenance statement exists in a public log. |

### Task 7: Enhance Verification Tooling

| Action | Details |
|---|---|
| **Objective** | Provide a single verification script that checks all provenance layers. |
| **Steps** | 1. Extend existing verification logic to check:<br>   – C2PA manifest signature and trust status.<br>   – PKI PDF signature validity.<br>   – OpenTimestamps proof against Bitcoin blockchain.<br>   – SCITT receipt verification.<br>2. Generate a human‑readable verification report. |
| **Dependencies** | Completion of Tasks 1–6. |
| **Output** | `verify_provenance.py` script that produces a comprehensive trust report. |

### Task 8: Update Build Pipeline Integration

| Action | Details |
|---|---|
| **Objective** | Integrate all provenance steps into the existing Quarto build system (`build.py`). |
| **Steps** | 1. Modify `sign_c2pa.py` to use production certificate and TSA.<br>2. Add a post‑render hook that calls PKI signing, OTS, and SCITT registration.<br>3. Store all artifacts (`.c2pa`, `.ots`, receipts) alongside outputs.<br>4. Add verification step to CI/CD pipeline. |
| **Dependencies** | Completion of Tasks 1–7. |
| **Output** | Fully integrated build pipeline producing verifiably provident PDFs. |



## 6. Alternative Solution Evaluation

| Solution | Strengths | Weaknesses | C2PA Compatibility |
|---|---|---|---|
| **C2PA (primary)** | Industry backing, open standard, hard binding to asset, rich assertions | Trust List still maturing, limited PDF tooling | N/A |
| **PKI + PAdES** | Mature, legally recognized, widely supported | Does not capture editing history, weaker AI provenance | Complementary |
| **SCITT** | Public transparency, append‑only logs, IETF standard | Requires separate infrastructure, no asset binding | Complementary |
| **OpenTimestamps** | Trustless, blockchain‑anchored, quantum‑resistant | Slow confirmation (~60 min), requires Bitcoin access | Complementary |
| **W3C Verifiable Credentials** | Decentralized, flexible, W3C standard | Requires DID infrastructure, no asset binding | Complementary |
| **KERI** | Decentralized key management, no ledger required | Less mature ecosystem, higher complexity | Complementary |
| **Truepic Lens** | Production‑ready SDK, integrated C2PA + capture verification | Proprietary, vendor lock‑in | Built on C2PA |



## 7. Recommendations

1. **Immediately acquire a production C2PA certificate** from SSL.com or DigiCert to replace the test certificate. This is the single most critical step for trust.

2. **Implement RFC 3161 timestamping** in all C2PA manifests. Without timestamps, manifests become invalid when the certificate expires.

3. **Deploy OpenTimestamps as a backup trust anchor** – it provides independent, trustless verification that does not rely on CAs or TSAs.

4. **Implement PKI PDF signatures (PAdES) alongside C2PA** – this provides a legally mature, independently verifiable proof of authorship.

5. **Adopt SCITT transparency logging** for all provenance statements – this creates a public, auditable record that cannot be retroactively altered.

6. **Enhance verification tooling** to cross‑validate all layers (C2PA, PKI, OTS, SCITT). The strength of the system lies in redundancy of trust mechanisms.

7. **Monitor C2PA Trust List evolution** – as more CAs join the Conformance Programme, the trust infrastructure will mature. Participate in the C2PA Conformance Programme if organization‑level certification is desired.

8. **Maintain backward compatibility** – ensure that the existing `sign_c2pa.py` script continues to work during the transition, with the new features added as optional enhancements.



## Conclusion

The current test‑certificate implementation of C2PA provides a solid foundation for IP provenance but is not production‑ready due to the lack of a trusted certificate chain and timestamps. By migrating to a production C2PA certificate, adding RFC 3161 timestamps, and integrating complementary solutions (PKI signatures, OpenTimestamps, SCITT transparency), a robust, cross‑verified IP protection system can be achieved. The proposed tasks outline a clear, phased migration path that preserves existing functionality while adding independent verification layers. This multi‑layered approach ensures that even if one trust mechanism is compromised or fails, others remain verifiable, providing defense‑in‑depth for intellectual property authentication.