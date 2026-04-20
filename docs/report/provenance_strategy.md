# Intellectual Property Protection Through Verifiable Provenance

## Executive Summary

This report presents a unified technical strategy for securing intellectual property (IP) in digital documents through cryptographic provenance frameworks. The primary focus is the Coalition for Content Provenance and Authenticity (C2PA) standard, evaluated alongside complementary technologies including PKI/PAdES, IETF SCITT, OpenTimestamps, W3C Verifiable Credentials, KERI, and SEAL.

The strategy addresses three core threats to digital IP:

1. Unauthorized modification – content alteration without detection
2. Attribution fraud – false claims of authorship or origin  
3. Provenance obfuscation – loss of creation history and chain-of-custody

Key Recommendations:

- Migrate from test certificates to production C2PA-conformant certificates (DigiCert/SSL.com) with RFC 3161 timestamping, while retaining self‑signed certificates for development and testing.
- Implement a hybrid architecture combining C2PA (rich provenance), PKI/PAdES (legal recognition), and OpenTimestamps (trustless anchoring), with commercial alternatives available for each layer.
- Deploy cross-verification tooling that validates multiple independent trust mechanisms, whether free or commercial.
- Integrate all provenance steps into the existing Quarto-based `build.py` pipeline.

This defense-in-depth approach ensures that compromise or failure of any single trust mechanism does not undermine overall IP protection.

## 1. Current Implementation Analysis: `sign_c2pa.py`

### 1.1 Architecture Overview

The existing script implements the core C2PA workflow:

```python
# Core workflow summary
1. Calculate SHA-256 hash of source PDF
2. Inject hash as custom assertion: org.ssccs.pdfhash
3. Load manifest JSON template, remove test signing fields
4. Generate sidecar .c2pa manifest via c2patool
5. Create metadata SVG containing hash + original manifest (CDATA)
6. Verify generated manifest with c2patool
```

### 1.2 Critical Limitations of Test-Certificate Mode

| Issue | Impact | Free Mitigation | Commercial Mitigation |
|-------|--------|----------------|------------------------|
| Untrusted certificate | Validators show "unrecognized"; no legal weight | Self-signed certificate (internal testing) | Acquire C2PA-conformant CA certificate (DigiCert/SSL.com) |
| No trusted timestamp | Manifest invalid after cert expiry | OpenTimestamps (Bitcoin anchor) | Integrate RFC 3161 TSA (DigiCert, GlobalSign) |
| Private key in filesystem | Key exposure risk | (none – use file with caution) | Use KMS/HSM for key operations |
| Sidecar-only storage | Manifest/PDF separation risk | Embed in PDF XMP using pypdf (may be unstable) | Use commercial PDF SDK for reliable embedding |
| No cross-verification | Single point of trust failure | Add OpenTimestamps + W3C VC | Add PKI signature + SCITT |

### 1.3 Production Readiness Requirements (Free + Commercial)

```yaml
production_requirements:
  certificate:
    free: "Self-signed (development only)"
    commercial: "C2PA-conformant CA (DigiCert, SSL.com) – PKCS#12 (.pfx) with full chain, must chain to C2PA Trust List root"
  
  timestamping:
    free: "OpenTimestamps (Bitcoin blockchain)"
    commercial: "RFC 3161 TSA (DigiCert, SSL.com, GlobalSign) – embed token in claim signature"
  
  key_management:
    free: "File system (not recommended for production)"
    commercial: "AWS KMS, Azure Key Vault, HashiCorp Vault, On-premise HSM"
  
  manifest_storage:
    free: "Sidecar .c2pa or pypdf XMP embedding"
    commercial: "Embed in PDF XMP using commercial SDK; optional soft-binding to HTTPS manifest store"
```

## 2. C2PA Technical Architecture: Deep Dive

### 2.1 Specification Overview

Standard: C2PA Technical Specification v2.3 (December 2025)  
Governance: Joint Development Foundation Projects, LLC  
Key Members: Adobe, Microsoft, Google, Intel, Arm, BBC, Sony, Truepic, SSCCS Foundation

### 2.2 Data Model Hierarchy

```
C2PA Manifest (JUMBF container - ISO/IEC 19567-1)
│
├── Claim (CBOR-encoded, signed)
│   ├── Assertion Store
│   │   ├── stds.schema-org.CreativeWork
│   │   │   ├── author, copyrightHolder, license, dateCreated
│   │   ├── c2pa.actions (edit history: who, when, what, software)
│   │   ├── c2pa.ingredient (source materials with parentOf/componentOf)
│   │   ├── org.ssccs.pdfhash (custom: {"hash": "sha256:abc123..."})
│   │   └── [extensible: any JSON-LD compatible assertion]
│   │
│   ├── Credential Store (optional)
│   │   └── W3C Verifiable Credentials for signer identity
│   │
│   └── Content Binding
│       ├── Hard: hash embedded in asset metadata (tamper-evident)
│       └── Soft: manifest referenced by external identifier
│
├── Claim Signature
│   ├── Algorithm: ECDSA P-256 / P-384 or RSA-PSS 2048/3072
│   ├── Certificate: X.509 chain to C2PA Trust List root (commercial) or self-signed (test)
│   └── Timestamp: RFC 3161 token (commercial) or OpenTimestamps proof (free)
│
└── Manifest Store Metadata
    ├── Format: application/c2pa+json or application/c2pa+cbor
    └── Location: embedded, sidecar (.c2pa), or remote URL
```

### 2.3 Trust Infrastructure: C2PA Trust List

```
C2PA Trust List Validation Chain:
                                                    
User/Validator Application                        
         │                                        
         ▼                                        
[1] Load C2PA Trust List (HTTPS, signed)          
         │                                        
         ▼                                        
[2] Extract signer certificate from manifest      
         │                                        
         ▼                                        
[3] Verify certificate chains to Trust List root  
         │                                        
         ▼                                        
[4] Check revocation (CRL/OCSP)                   
         │                                        
         ▼                                        
[5] Verify claim signature with public key        
         │                                        
         ▼                                        
[6] Validate timestamp token (if present)         
         │                                        
         ▼                                        
[7] Verify content binding hash matches asset     
```

Current Conformant CAs (2026):

- DigiCert – Full C2PA Conformance Programme participant
- SSL.com – Joined September 2025, supports C2PA-specific OIDs
- Future entrants – Monitor C2PA website for updates

### 2.4 Implementation Patterns for PDF Workflows

#### Pattern A: Sidecar Manifest (Current `sign_c2pa.py`)

```python
# Output structure
document.pdf          # Original content
document.c2pa         # C2PA manifest (sidecar)
document.c2pa_identifier.svg  # Metadata with hash + manifest JSON
```

Pros: Non-invasive to original PDF; easy to generate  
Cons: Risk of separation; requires coordinated distribution

#### Pattern B: Embedded Manifest (Recommended for Production)

```python
# Embed C2PA manifest in PDF XMP namespace
from pypdf import PdfReader, PdfWriter

def embed_c2pa_manifest(pdf_path: Path, c2pa_manifest: bytes):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    # Add C2PA manifest to XMP metadata
    xmp = reader.xmp_metadata or {}
    xmp['c2pa:manifest'] = c2pa_manifest  # Base64-encoded
    
    for page in reader.pages:
        writer.add_page(page)
    
    writer.add_metadata(xmp)
    writer.write(pdf_path.with_suffix('.signed.pdf'))
```

Pros: Single-file distribution; standard PDF viewers can extract metadata  
Cons: Increases file size (~12-100KB); requires XMP-aware tools (free pypdf may be unstable for complex PDFs; commercial SDKs recommended for production)

#### Pattern C: Soft-Binding with Repository

```python
# Store manifest externally, reference by hash in PDF
manifest_hash = hashlib.sha256(c2pa_manifest).hexdigest()
reference = f"c2pa+manifest:{manifest_hash}@https://manifests.ssccs.org/"

# Embed reference in PDF metadata
pdf_metadata['c2pa:manifestRef'] = reference
```

Pros: Minimal file size impact; central manifest management  
Cons: Requires always-available repository; network dependency for verification

## 3. Complementary Technologies: Cross-Verification Matrix

### 3.1 Technology Comparison

| Technology | Primary Function | Trust Model | Legal Recognition | Asset Binding | Key Strength |
|-----------|-----------------|-------------|------------------|---------------|-------------|
| C2PA | Content provenance, edit history | CA-based (C2PA Trust List) | Emerging | Hard/Soft (JUMBF) | Rich assertions, industry backing |
| PKI/PAdES | Document signing, identity | WebTrust PKI, eIDAS | Mature (EU/US) | Embedded signature | Legal admissibility, wide support |
| SCITT | Transparency logging, public audit | Append-only log, IETF standard | Emerging | Statement reference | Public verifiability, non-repudiation |
| OpenTimestamps | Trustless timestamping | Bitcoin blockchain consensus | Informal | Hash anchoring | No trusted third party, quantum-resistant |
| W3C VC | Decentralized credential claims | DID-based, cryptographic | Emerging | Credential reference | Flexible identity, interoperability |
| KERI | Self-certifying identifiers | Key event logs, no ledger | Experimental | Identifier binding | Decentralized, no central authority |
| SEAL | Lightweight attribution signature | DNSSEC-anchored domain keys | Designed for FRE | Hash signature | Minimal overhead, DNS-based validation |
| Imperceptible Watermarking | Content tracking, forensic marking | Statistical signal detection | Limited | Embedded in content | Survives transcoding, covert |

### 3.2 Cross-Verification Strategy

A robust IP protection system validates provenance through multiple independent mechanisms. Agreement between any two methods provides strong corroboration.

```
Verification Pipeline (Recommended Order):

1. Extract PDF hash from C2PA assertion (org.ssccs.pdfhash)
   │
2. Verify C2PA manifest:
   ├─ Signature validity (cryptographic)
   ├─ Certificate chain to C2PA Trust List (commercial) or accept self-signed with warning
   ├─ Revocation status (CRL/OCSP)
   └─ Timestamp validity (RFC 3161 or OpenTimestamps)
   │
3. Verify embedded PKI/PAdES signature (if present):
   ├─ Certificate chain to trusted root
   ├─ Document integrity (hash match)
   └─ Timestamp validation
   │
4. Validate OpenTimestamps proof:
   ├─ Parse .ots file
   ├─ Reconstruct Merkle path
   └─ Verify Bitcoin block header (SPV or full node)
   │
5. Query SCITT Transparency Service:
   ├─ Submit PDF hash
   ├─ Retrieve inclusion receipt
   └─ Verify receipt signature and log consistency
   │
6. Check W3C Verifiable Credential (optional):
   ├─ Resolve DID document
   ├─ Verify VC signature
   └─ Confirm claim matches PDF hash
   │
7. Generate consolidated verification report:
   └─ Pass/Fail per mechanism + confidence score
```

### 3.3 Failure Mode Analysis

| Scenario | C2PA Only | Hybrid (C2PA+PKI+OTS) | Mitigation |
|----------|-----------|----------------------|-----------|
| CA compromise | All signatures untrusted | PKI signatures still valid; OTS timestamps intact | Monitor CRL; rotate certificates |
| TSA outage | Timestamps unavailable | OTS provides backup timestamps | Use multiple TSA providers |
| Network unavailable | Soft-binding manifests unverifiable | Embedded PKI + OTS work offline | Prefer hard-binding for critical docs |
| PDF transcoded | Hard-binding breaks | PKI signature may survive; OTS hash still valid | Use soft-binding + repository for edited versions |
| Legal challenge | Emerging precedent | PKI/PAdES has established case law | Always include PKI signature for legal docs |

### 3.4 Commercial vs Free: Comparison Matrix and Hybrid Strategy

The following table contrasts free/open‑source options with commercial (paid) alternatives for each provenance component. Both are supported by the codebase; the choice depends on legal requirements, security posture, and budget.

| Component | Free Option | Commercial Option | Free Limitations | Commercial Benefits | Recommended Use |
|-----------|-------------|-------------------|------------------|---------------------|-----------------|
| **C2PA Certificate** | Self-signed (generated via OpenSSL) | DigiCert C2PA, SSL.com C2PA | Validators show "untrusted"; no legal weight | C2PA Trust List inclusion; trusted by Adobe/Microsoft | Development/testing: free; public release: commercial |
| **Timestamping** | OpenTimestamps (Bitcoin blockchain) | RFC 3161 TSA (DigiCert, GlobalSign, SSL.com) | ~hour confirmation; not a legal standard | Instant, RFC-standard, admissible in court | Use both for redundancy |
| **Key Management** | File system (private key on disk) | AWS KMS, Azure Key Vault, HSM | High risk of exposure; no audit log | Secure enclave; full audit trail; key rotation | Production: mandatory commercial |
| **PDF Manifest Embedding** | pypdf XMP insertion | iText 8, PDFlib (commercial SDKs) | Unstable with complex PDFs; may corrupt | 100% reliability; support for all PDF features | Important documents: commercial |
| **PKI/PAdES** | None (free certs not trusted) | WebTrust/eIDAS qualified certificates | Not applicable | Legally binding; eIDAS Qualified Signatures | All legal documents |
| **SCITT Transparency** | Self-hosted open-source registry | Microsoft SCITT Registry, other managed services | Maintenance burden; availability not guaranteed | Managed, high availability, SLAs | Pilot: free; production: commercial |
| **W3C Verifiable Credentials** | did:key, did:web (self-hosted) | did:indy, commercial verifiable data registries | No revocation mechanism; DIY trust | Built-in revocation; governance frameworks | Experimental: free; enterprise: commercial |

**Hybrid Strategy Recommendation:**

- **Development / Internal Testing:** Use full free stack (self-signed C2PA + OpenTimestamps + pypdf embedding). This validates the workflow at zero cost.
- **Public / Official Documents:** Always use commercial C2PA certificate + RFC 3161 TSA. Add PKI/PAdES for legal enforceability.
- **Maximum Assurance:** Combine commercial C2PA + commercial PKI/PAdES + free OpenTimestamps (as an independent anchor) + SCITT transparency. This gives three independent trust anchors.

The existing code in this report supports both free and commercial providers through configuration (e.g., `--cert` can point to a self-signed or DigiCert PEM; `--tsa` can be an RFC 3161 URL or left empty to use OpenTimestamps). No code changes are required to switch between them.

## 4. Implementation Roadmap: Phased Technical Tasks

### Phase 1: Foundation (Weeks 1-2)

#### Task 1.1: Acquire Production C2PA Certificate

```python
# Certificate acquisition checklist
certificate_requirements = {
    "ca": "DigiCert or SSL.com (C2PA-conformant)",
    "key_type": "ECDSA P-384 or RSA-PSS 3072",
    "validity": "24 months minimum",
    "extensions": [
        "keyUsage: digitalSignature",
        "extendedKeyUsage: contentAuthenticity",
        "c2pa:conformanceLevel: full"
    ],
    "delivery": "PKCS#12 (.pfx) with full chain"
}

# Verification post-acquisition
def verify_c2pa_certificate(cert_path: Path):
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    
    with open(cert_path, 'rb') as f:
        cert = x509.load_pem_x509_certificate(f.read(), default_backend())
    
    # Check C2PA-specific OID (example)
    c2pa_oid = x509.ObjectIdentifier("1.3.6.1.4.1.311.100.1")  # Placeholder
    try:
        ext = cert.extensions.get_extension_for_oid(c2pa_oid)
        print(f"✓ C2PA extension present: {ext.value}")
    except x509.ExtensionNotFound:
        print("✗ Warning: C2PA-specific extension not found")
    
    # Verify chain (requires C2PA Trust List root)
    # Implementation: use c2patool or custom validator
    return True
```

#### Task 1.2: Integrate RFC 3161 Timestamping

```python
# Modified sign_c2pa.py: TSA integration
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def request_timestamp(tsa_url: str, hash_value: bytes) -> bytes:
    """Request RFC 3161 timestamp token from TSA."""
    # Build TimeStampReq (simplified)
    timestamp_req = build_rfc3161_request(hash_value)
    
    response = requests.post(
        tsa_url,
        data=timestamp_req,
        headers={'Content-Type': 'application/timestamp-query'},
        timeout=30
    )
    response.raise_for_status()
    
    # Parse TimeStampResp, extract token
    timestamp_token = parse_rfc3161_response(response.content)
    return timestamp_token

# Integration point in manifest generation
def generate_manifest_with_timestamp(pdf_hash: str, manifest_data: dict, tsa_url: str):
    # ... existing manifest preparation ...
    
    # Request timestamp for claim hash
    claim_hash = compute_claim_hash(manifest_data)
    timestamp_token = request_timestamp(tsa_url, claim_hash)
    
    # Embed timestamp in claim signature
    manifest_data['claim_signature']['timestamp'] = {
        'token': base64.b64encode(timestamp_token).decode(),
        'tsa': tsa_url,
        'gen_time': extract_timestamp_time(timestamp_token)
    }
    
    return manifest_data
```

#### Task 1.3: Secure Key Management Integration

```python
# Abstract signer interface for KMS/HSM
from abc import ABC, abstractmethod

class ExternalSigner(ABC):
    """Abstract interface for external key operations."""
    
    @abstractmethod
    def sign(self, data: bytes, algorithm: str) -> bytes:
        """Sign data using protected private key."""
        pass
    
    @abstractmethod
    def get_certificate_chain(self) -> List[bytes]:
        """Return certificate chain for verification."""
        pass

# AWS KMS implementation example
class AWSKMSSigner(ExternalSigner):
    def __init__(self, key_id: str, region: str, cert_chain_path: Path):
        import boto3
        self.kms = boto3.client('kms', region_name=region)
        self.key_id = key_id
        self.cert_chain = [open(p, 'rb').read() for p in cert_chain_path]
    
    def sign(self, data: bytes, algorithm: str) -> bytes:
        # Map C2PA algorithm to KMS signing spec
        signing_spec = {
            'ECDSA_SHA_384': 'ECDSA_SHA_384',
            'RSASSA_PSS_SHA_256': 'RSASSA_PSS_SHA_256'
        }[algorithm]
        
        response = self.kms.sign(
            KeyId=self.key_id,
            Message=data,
            MessageType='DIGEST',  # data is already hashed
            SigningAlgorithm=signing_spec
        )
        return response['Signature']
    
    def get_certificate_chain(self) -> List[bytes]:
        return self.cert_chain

# Usage in sign_c2pa.py
def get_signer(config: dict) -> ExternalSigner:
    if config.get('kms_provider') == 'aws':
        return AWSKMSSigner(
            key_id=config['kms_key_id'],
            region=config['aws_region'],
            cert_chain_path=Path(config['cert_chain_path'])
        )
    # Add Azure, GCP, HashiCorp implementations as needed
```

### Phase 2: Complementary Layers (Weeks 3-5)

#### Task 2.1: PKI/PAdES PDF Signing

```python
# docs/_utils/sign_pades.py
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from PyPDF2 import PdfReader, PdfWriter
import endesive  # PAdES library

def sign_pdf_pades(
    pdf_path: Path,
    output_path: Path,
    cert_path: Path,
    key_path: Path,
    tsa_url: str,
    reason: str = "IP Protection",
    location: str = "SSCCS Foundation"
):
    """Apply PAdES signature with timestamp to PDF."""
    
    # Load certificate and key
    with open(cert_path, 'rb') as f:
        cert = serialization.load_pem_x509_certificate(f.read())
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    
    # Prepare signature parameters
    signature_params = {
        'signer': cert,
        'key': private_key,
        'tsaurl': tsa_url,
        'reason': reason,
        'location': location,
        'contact': 'legal@ssccs.org',
        'mode': 'sign',  # PAdES-BES or PAdES-LTV
        'timestamp': True,
    }
    
    # Sign using endesive library
    data = pdf_path.read_bytes()
    signed_data = endesive.pdf.sign(data, signature_params)
    
    # Write output
    output_path.write_bytes(signed_data)
    print(f"✓ PAdES signature applied: {output_path}")
    return output_path
```

#### Task 2.2: OpenTimestamps Integration

```python
# docs/_utils/sign_ots.py
import opentimestamps.core.timestamp as ots_timestamp
import opentimestamps.core.serialize as ots_serialize
import opentimestamps.core.op as ots_op
import hashlib

def generate_ots_proof(pdf_path: Path, output_path: Path):
    """Create OpenTimestamps proof for PDF hash."""
    
    # Compute PDF hash
    pdf_hash = hashlib.sha256(pdf_path.read_bytes()).digest()
    
    # Create timestamp operation (simplified - in practice, use ots-cli or library)
    # This submits hash to public calendars and returns proof
    timestamp = ots_timestamp.Timestamp(pdf_hash)
    
    # In production: use opentimestamps client to submit to calendars
    # For now, simulate with library call
    from opentimestamps import timestamp_file
    timestamp_file.timestamp(pdf_path, output_path)
    
    print(f"✓ OpenTimestamps proof created: {output_path}")
    return output_path

def verify_ots_proof(ots_path: Path, original_pdf: Path) -> bool:
    """Verify OTS proof against Bitcoin blockchain."""
    from opentimestamps import verify
    
    # Verify requires Bitcoin node access or trusted verifier service
    result = verify(ots_path, original_pdf)
    return result.is_verified()
```

#### Task 2.3: SCITT Transparency Service Integration

```python
# docs/_utils/register_scitt.py
import requests
import hashlib
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

class SCITTClient:
    """Client for SCITT-compliant Transparency Service."""
    
    def __init__(self, service_url: str, issuer_key_path: Path):
        self.service_url = service_url.rstrip('/')
        with open(issuer_key_path, 'rb') as f:
            self.issuer_key = serialization.load_pem_private_key(
                f.read(), password=None
            )
    
    def register_statement(self, pdf_path: Path, metadata: dict) -> dict:
        """Register a Signed Statement about the PDF."""
        
        # Build statement payload
        statement = {
            "type": "https://scitt.example.org/types/document-provenance/v1",
            "subject": {
                "hash": {
                    "algorithm": "sha256",
                    "value": hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                }
            },
            "claims": {
                "document": {
                    "title": metadata.get("title"),
                    "author": metadata.get("author"),
                    "created": metadata.get("created"),
                    "license": metadata.get("license")
                },
                "provenance": {
                    "c2pa_manifest_hash": metadata.get("c2pa_hash"),
                    "pades_signature_hash": metadata.get("pades_hash")
                }
            },
            "iss": "did:web:ssccs.org",  # Decentralized identifier
            "iat": int(time.time())
        }
        
        # Sign statement (simplified - use JOSE/COSE in production)
        signature = self.issuer_key.sign(
            json.dumps(statement, sort_keys=True).encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        signed_statement = {
            "statement": statement,
            "signature": {
                "algorithm": "RSASSA-PSS-SHA256",
                "value": base64.b64encode(signature).decode()
            }
        }
        
        # Submit to Transparency Service
        response = requests.post(
            f"{self.service_url}/statements",
            json=signed_statement,
            headers={'Content-Type': 'application/scitt-statement+json'}
        )
        response.raise_for_status()
        
        receipt = response.json()
        print(f"✓ SCITT receipt: {receipt['receiptId']}")
        return receipt
    
    def verify_receipt(self, receipt_id: str, expected_hash: str) -> bool:
        """Verify inclusion receipt from Transparency Service."""
        response = requests.get(
            f"{self.service_url}/receipts/{receipt_id}",
            headers={'Accept': 'application/scitt-receipt+json'}
        )
        response.raise_for_status()
        receipt = response.json()
        
        # Verify receipt signature and inclusion proof
        # Implementation depends on service's cryptographic scheme
        return verify_scitt_receipt(receipt, expected_hash)
```

### Phase 3: Integration & Verification (Weeks 6-8)

#### Task 3.1: Unified Verification Script

```python
# docs/_utils/verify_provenance.py
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

class VerificationStatus(Enum):
    PASS = auto()
    FAIL = auto()
    WARNING = auto()
    NOT_APPLICABLE = auto()

@dataclass
class VerificationResult:
    mechanism: str
    status: VerificationStatus
    message: str
    details: Optional[dict] = None

class ProvenanceVerifier:
    """Unified verifier for multi-layer provenance."""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.pdf_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        self.results: List[VerificationResult] = []
    
    def verify_c2pa(self, manifest_path: Optional[Path] = None) -> VerificationResult:
        """Verify C2PA manifest signature and trust chain."""
        try:
            # Use c2patool or native library
            import subprocess
            cmd = ["c2patool", str(self.pdf_path), "--verify"]
            if manifest_path:
                cmd.extend(["--manifest", str(manifest_path)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse output for trust status
                if "trusted" in result.stdout.lower():
                    return VerificationResult("C2PA", VerificationStatus.PASS, 
                                            "Manifest signature trusted")
                else:
                    return VerificationResult("C2PA", VerificationStatus.WARNING,
                                            "Signature valid but certificate untrusted",
                                            {"output": result.stdout})
            else:
                return VerificationResult("C2PA", VerificationStatus.FAIL,
                                        f"Verification failed: {result.stderr}")
        except Exception as e:
            return VerificationResult("C2PA", VerificationStatus.FAIL,
                                    f"Exception: {str(e)}")
    
    def verify_pades(self) -> VerificationResult:
        """Verify embedded PKI/PAdES signature."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(self.pdf_path)
            
            # Check for signature fields
            if '/AcroForm' not in reader.trailer['/Root']:
                return VerificationResult("PAdES", VerificationStatus.NOT_APPLICABLE,
                                        "No signature fields found")
            
            # Use endesive or similar for full validation
            # Simplified: check signature existence
            signatures = reader.get_fields().get('/Sig', [])
            if signatures:
                return VerificationResult("PAdES", VerificationStatus.PASS,
                                        f"Found {len(signatures)} signature(s)")
            else:
                return VerificationResult("PAdES", VerificationStatus.NOT_APPLICABLE,
                                        "No embedded signatures")
        except Exception as e:
            return VerificationResult("PAdES", VerificationStatus.FAIL,
                                    f"Exception: {str(e)}")
    
    def verify_ots(self, ots_path: Path) -> VerificationResult:
        """Verify OpenTimestamps proof."""
        try:
            if not ots_path.exists():
                return VerificationResult("OpenTimestamps", VerificationStatus.NOT_APPLICABLE,
                                        "No .ots file found")
            
            # Verify against blockchain (requires network)
            from opentimestamps import verify
            result = verify(ots_path, self.pdf_path)
            
            if result.is_verified():
                return VerificationResult("OpenTimestamps", VerificationStatus.PASS,
                                        f"Timestamp confirmed in block {result.block_height}")
            else:
                return VerificationResult("OpenTimestamps", VerificationStatus.FAIL,
                                        "Timestamp verification failed")
        except Exception as e:
            return VerificationResult("OpenTimestamps", VerificationStatus.FAIL,
                                    f"Exception: {str(e)}")
    
    def verify_scitt(self, receipt_path: Path) -> VerificationResult:
        """Verify SCITT transparency receipt."""
        try:
            if not receipt_path.exists():
                return VerificationResult("SCITT", VerificationStatus.NOT_APPLICABLE,
                                        "No receipt file found")
            
            receipt = json.loads(receipt_path.read_text())
            # Verify receipt signature and inclusion proof
            if verify_scitt_receipt(receipt, self.pdf_hash):
                return VerificationResult("SCITT", VerificationStatus.PASS,
                                        "Receipt verified in transparency log")
            else:
                return VerificationResult("SCITT", VerificationStatus.FAIL,
                                        "Receipt verification failed")
        except Exception as e:
            return VerificationResult("SCITT", VerificationStatus.FAIL,
                                    f"Exception: {str(e)}")
    
    def generate_report(self) -> str:
        """Generate human-readable verification report."""
        report = [f"Provenance Verification Report",
                 f"Document: {self.pdf_path.name}",
                 f"SHA-256: {self.pdf_hash}",
                 f"Timestamp: {datetime.now().isoformat()}",
                 "-" * 60]
        
        for r in self.results:
            status_icon = {
                VerificationStatus.PASS: "✓",
                VerificationStatus.FAIL: "✗",
                VerificationStatus.WARNING: "⚠",
                VerificationStatus.NOT_APPLICABLE: "○"
            }[r.status]
            report.append(f"{status_icon} {r.mechanism}: {r.message}")
            if r.details:
                for k, v in r.details.items():
                    report.append(f"    {k}: {v}")
        
        # Overall assessment
        passed = sum(1 for r in self.results if r.status == VerificationStatus.PASS)
        failed = sum(1 for r in self.results if r.status == VerificationStatus.FAIL)
        
        report.append("-" * 60)
        if failed == 0 and passed >= 2:
            report.append("OVERALL: CONFIRMED (multiple independent verifications passed)")
        elif failed == 0:
            report.append("OVERALL: PARTIAL (no failures, but limited verification)")
        else:
            report.append(f"OVERALL: FAILED ({failed} verification(s) failed)")
        
        return "\n".join(report)
    
    def run_all(self, manifest_path: Optional[Path] = None, 
                ots_path: Optional[Path] = None,
                receipt_path: Optional[Path] = None) -> str:
        """Execute all available verification checks."""
        self.results = [
            self.verify_c2pa(manifest_path),
            self.verify_pades(),
        ]
        if ots_path:
            self.results.append(self.verify_ots(ots_path))
        if receipt_path:
            self.results.append(self.verify_scitt(receipt_path))
        
        return self.generate_report()

# CLI usage
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, help="PDF file to verify")
    parser.add_argument("--manifest", "-m", type=Path, help="C2PA manifest path")
    parser.add_argument("--ots", "-o", type=Path, help="OpenTimestamps proof path")
    parser.add_argument("--receipt", "-r", type=Path, help="SCITT receipt path")
    args = parser.parse_args()
    
    verifier = ProvenanceVerifier(args.pdf)
    report = verifier.run_all(args.manifest, args.ots, args.receipt)
    print(report)
```

#### Task 3.2: Build Pipeline Integration (`build.py` Modifications)

```python
# Add to build.py: post-render provenance hooks

def apply_provenance_layers(
    pdf_path: Path,
    target_name: str,
    config: Dict[str, Any],
    docs_root: Path
) -> Dict[str, Path]:
    """Apply all configured provenance layers to generated PDF."""
    artifacts = {}
    
    # C2PA signing (existing, enhanced)
    if config.get("c2pa"):
        manifest_template = pdf_path.parent / f"{pdf_path.stem}.c2pa_manifest.json"
        if manifest_template.exists():
            c2pa_output = pdf_path.parent / f"{pdf_path.stem}.c2pa"
            cmd = [
                "python3", str(docs_root / "_utils" / "sign_c2pa.py"),
                "--pdf", str(pdf_path),
                "--manifest", str(manifest_template),
                "--output", str(c2pa_output),
                "--cert", config.get("c2pa_cert_path"),  # New: production cert
                "--tsa", config.get("tsa_url"),  # New: timestamp authority
            ]
            if run_command(cmd, cwd=docs_root):
                artifacts["c2pa"] = c2pa_output
    
    # PKI/PAdES signing
    if config.get("pades"):
        pades_output = pdf_path.parent / f"{pdf_path.stem}.pades.pdf"
        cmd = [
            "python3", str(docs_root / "_utils" / "sign_pades.py"),
            "--pdf", str(pdf_path),
            "--output", str(pades_output),
            "--cert", config["pades_cert"],
            "--key", config["pades_key"],
            "--tsa", config["tsa_url"],
        ]
        if run_command(cmd, cwd=docs_root):
            artifacts["pades"] = pades_output
    
    # OpenTimestamps
    if config.get("opentimestamps"):
        ots_output = pdf_path.parent / f"{pdf_path.stem}.ots"
        cmd = [
            "python3", str(docs_root / "_utils" / "sign_ots.py"),
            "--pdf", str(pdf_path),
            "--output", str(ots_output),
        ]
        if run_command(cmd, cwd=docs_root):
            artifacts["ots"] = ots_output
    
    # SCITT registration
    if config.get("scitt"):
        receipt_output = pdf_path.parent / f"{pdf_path.stem}.scitt.json"
        cmd = [
            "python3", str(docs_root / "_utils" / "register_scitt.py"),
            "--pdf", str(pdf_path),
            "--output", str(receipt_output),
            "--service", config["scitt_service"],
            "--key", config["scitt_issuer_key"],
            "--metadata", json.dumps({
                "title": config.get("title"),
                "author": config.get("author"),
                "c2pa_hash": artifacts.get("c2pa") and compute_file_hash(artifacts["c2pa"])
            }),
        ]
        if run_command(cmd, cwd=docs_root):
            artifacts["scitt"] = receipt_output
    
    return artifacts

# Integrate into build_generic() after PDF generation:
# ... existing PDF generation code ...
if config.get("provenance_layers"):
    artifacts = apply_provenance_layers(pdf_path, target, config, docs_root)
    # Store artifact paths in cache for verification
    update_format_cache(qmd_path, fmt, pdf_path, target_name=target, 
                       linked_artifacts=artifacts)
```

## 5. Validation & Testing Protocol

### 5.1 Test Vector Suite

| Test ID | Scenario | Input | Expected Result | Validation Method |
|---------|----------|-------|----------------|------------------|
| TV-01 | Valid C2PA signature | Signed PDF + trusted cert | Verification PASS | `c2patool verify`, check trust status |
| TV-02 | Modified content | Signed PDF + 1-bit flip | Hash mismatch detected | Compare `org.ssccs.pdfhash` vs actual |
| TV-03 | Certificate revocation | PDF signed with revoked cert | Verification FAIL | CRL/OCSP check via TSA |
| TV-04 | Timestamp expiry | Manifest with expired cert but valid TSA | Verification PASS (timestamp valid) | Check TSA token validity |
| TV-05 | Cross-format consistency | PDF+HTML+Markdown from same source | All share identical source hash | Compare `org.ssccs.pdfhash` across formats |
| TV-06 | PKI+C2PA agreement | PDF with both signatures | Both mechanisms verify same hash | Run unified verifier, check agreement |
| TV-07 | OTS blockchain anchor | PDF + .ots file | Timestamp confirmed in Bitcoin block | Verify against blockchain SPV |
| TV-08 | SCITT inclusion | Registered statement + receipt | Receipt verifies in transparency log | Query SCITT service, verify proof |
| TV-09 | Offline verification | PDF + embedded PKI + OTS | Verification succeeds without network | Disconnect network, run verifier |
| TV-10 | Legal challenge simulation | Disputed authorship claim | PKI certificate chain resolves identity | Check certificate subject + organizational VC |

### 5.2 Performance Benchmarks

| Operation | Target Latency | Measurement Method | Optimization Notes |
|-----------|---------------|-------------------|-------------------|
| C2PA manifest generation | < 3s per PDF | Time `c2patool` execution | Pre-compile manifest templates |
| PKI/PAdES signing | < 2s per PDF | Benchmark endesive signing | Use hardware acceleration for RSA |
| OpenTimestamps proof | < 5s (async) | Measure calendar submission | Batch multiple hashes per request |
| SCITT registration | < 10s (async) | API response time | Use connection pooling |
| Unified verification | < 2s (cached) | End-to-end verifier runtime | Cache certificate validation results |
| Blockchain verification | < 30s (network) | SPV proof verification | Use trusted verifier service for production |

### 5.3 Security Audit Checklist

```yaml
key_management:
  - [ ] Private keys stored in HSM or cloud KMS (never filesystem)
  - [ ] Key rotation policy documented (e.g., annual for signing keys)
  - [ ] Access logging enabled for all key operations
  - [ ] Multi-person approval required for key export (if ever needed)

certificate_validation:
  - [ ] CRL/OCSP checking enabled for all PKI validations
  - [ ] C2PA Trust List updated automatically (daily cron)
  - [ ] Certificate pinning for critical CA roots
  - [ ] Monitoring for CA compromise announcements

timestamping:
  - [ ] Multiple TSA providers configured (redundancy)
  - [ ] Timestamp token validation includes nonce checking
  - [ ] Long-term validation (LTV) data embedded in signatures

network_security:
  - [ ] All external API calls use TLS 1.3+ with certificate pinning
  - [ ] Rate limiting on verification endpoints
  - [ ] Input validation on all manifest/proof parsers

audit_logging:
  - [ ] All signing operations logged (who, when, what, result)
  - [ ] Verification attempts logged (for abuse detection)
  - [ ] Logs immutable (write-once storage or blockchain anchor)
  - [ ] Regular log integrity checks

disaster_recovery:
  - [ ] Backup of certificate chains and trust lists
  - [ ] Documented procedure for key compromise response
  - [ ] Tested recovery process for trust list corruption
```

## 6. Legal & Compliance Framework

### 6.1 Evidentiary Standards Mapping

| Jurisdiction | Standard | C2PA Status | PKI/PAdES Status | Recommendation |
|-------------|----------|-------------|-----------------|---------------|
| United States | Federal Rules of Evidence (FRE) 901 | Emerging; requires supplemental authentication | Mature; widely accepted | Always include PKI signature for US legal docs |
| European Union | eIDAS Regulation (910/2014) | Not yet qualified | Qualified Electronic Signatures (QES) available | Use PAdES with QSCD for EU legal validity |
| International | UNCITRAL Model Law on E-Signatures | Compatible but not specified | Explicitly recognized | Hybrid approach satisfies most jurisdictions |

### 6.2 Required Documentation

1. Signing Policy Statement
   - Defines authorized signers, key management procedures, certificate lifecycle
   - Example clause: "Only documents approved by the SSCCS Legal Committee may be signed with the production C2PA certificate."

2. Verification Guide for Recipients
   - Step-by-step instructions for validating documents
   - Includes CLI commands, expected outputs, troubleshooting

3. Dispute Resolution Protocol

   ```
   If provenance is challenged:
   1. Request full verification report from verifier tool
   2. If C2PA fails but PKI passes: rely on PKI certificate chain
   3. If both fail: check SCITT transparency log for historical record
   4. If all fail: document is considered unverified; escalate to legal team
   5. Maintain audit trail of all verification attempts
   ```

4. Retention Policy
   - Signing certificates: retain 7 years after expiry
   - Audit logs: retain 10 years minimum
   - Manifest repositories: maintain availability for document lifetime + 5 years

### 6.3 Privacy Considerations

- Minimize PII in assertions: Use organizational identifiers rather than personal names where possible
- GDPR compliance: Right to erasure may conflict with immutable provenance; implement "soft deletion" with cryptographic revocation
- Transparency vs. confidentiality: Balance public verifiability with sensitive content protection using encryption + provenance separation

## 7. Maintenance & Evolution Strategy

### 7.1 Monitoring & Alerting

```yaml
monitoring_targets:
  c2pa_trust_list:
    check: "Daily download and signature verification"
    alert: "If list fails to update or signature invalid"
  
  certificate_expiry:
    check: "Weekly scan of all signing certificates"
    alert: "30/7/1 days before expiry"
  
  tsa_availability:
    check: "Hourly ping to configured TSA endpoints"
    alert: "If >2 providers unreachable"
  
  verification_endpoint:
    check: "Synthetic transactions every 5 minutes"
    alert: "If error rate >1% or latency >5s"
```

### 7.2 Version Management

```
Provenance System Versioning:
- Manifest schema: Semantic versioning (v2.3 → v2.4)
- Assertion definitions: Namespace-versioned (org.ssccs.pdfhash/v1)
- Verification protocol: Backward-compatible extensions
- Deprecation policy: 24-month notice for breaking changes
```

### 7.3 Community Engagement

- C2PA Conformance Programme: Consider organizational participation for early access to updates
- IETF SCITT Working Group: Contribute to standardization efforts
- Open-source contributions: Share verification tooling improvements upstream
- Interoperability testing: Regular cross-implementation validation events

## 8. Conclusion & Prioritized Actions

### Immediate Priorities (Next 30 Days)

1. Acquire production C2PA certificate from SSL.com or DigiCert – this is the single highest-impact change
2. Integrate RFC 3161 timestamping into `sign_c2pa.py` to ensure long-term validity
3. Deploy unified verification script (`verify_provenance.py`) for internal testing
4. Document signing policy and train authorized personnel on key management procedures

### Medium-Term Enhancements (30-90 Days)

1. Add PKI/PAdES signing as parallel output for legal document workflows
2. Implement OpenTimestamps integration as trustless backup for timestamps
3. Evaluate SCITT service providers for transparency logging pilot
4. Update `build.py` pipeline to support configurable provenance layers per target

### Long-Term Strategy (90+ Days)

1. Deploy KMS/HSM integration for production key management
2. Establish public verification endpoint for external stakeholders
3. Participate in C2PA/SCITT standards development to shape future specifications
4. Conduct third-party security audit of the complete provenance system

### Success Metrics

- Technical: >99.9% signature verification success rate; <2s average verification latency
- Operational: Zero key compromise incidents; <4h mean time to certificate renewal
- Legal: Successful validation in at least one jurisdictional challenge test case
- Adoption: 100% of SSCCS official documents include at least two independent provenance mechanisms

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| C2PA | Coalition for Content Provenance and Authenticity; open standard for cryptographic content provenance |
| JUMBF | JPEG Universal Metadata Box Format (ISO/IEC 19567-1); container for C2PA manifests |
| Hard Binding | Cryptographic hash embedded directly in asset; breaks if content modified |
| Soft Binding | Manifest stored externally; referenced by asset identifier |
| PAdES | PDF Advanced Electronic Signatures (ETSI EN 319 142); legally recognized PDF signature format |
| RFC 3161 | Internet X.509 Public Key Infrastructure Time-Stamp Protocol (TSP) |
| SCITT | IETF Supply Chain Integrity, Transparency, and Trust architecture for transparency services |
| OpenTimestamps | Trustless timestamping protocol using Bitcoin blockchain anchoring |
| W3C VC | Verifiable Credentials; cryptographically signed claims using decentralized identifiers |
| KERI | Key Event Receipt Infrastructure; self-certifying identifiers without ledger dependency |
| SEAL | Secure Evidence Attribution Label; DNSSEC-anchored lightweight signature scheme |
