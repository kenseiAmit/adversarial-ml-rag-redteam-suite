# Supply Chain Vulnerability Analysis

## Vulnerability Summary

Based on the automated Trivy container scan of the production image (`06_trivy_report.json`), a total of 804 vulnerabilities were detected across OS packages and application dependencies.

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 34 |
| MEDIUM | 160 |
| LOW | 601 |
| *UNKNOWN* | *9* |
| **Total** | **804** |

In addition, static code analysis of the deployment `Dockerfile` identified **6 configuration security issues** ranging from root user execution to unpinned base image tags.

---

## High Severity Findings

The following table highlights the most critical high-severity CVEs identified in the container image, their affected component packages, fixed versions, and security implications:

| CVE | Package | Fixed Version | Description |
|-----|---------|--------------|-------------|
| CVE-2026-24049 | `wheel` | 0.46.2 | Arbitrary Code Execution / Privilege Escalation via directory traversal and file permission modification during malicious wheel unpacking (`wheel.unpack`). |
| CVE-2026-23949 | `jaraco.context` | 6.1.0 | Zip Slip path traversal in `jaraco.context.tarball()` allowing attackers to extract malicious files outside intended working directories. |
| CVE-2026-25210 | `libexpat1` | 2.7.4 | Buffer reallocation integer overflow in XML parser leading to information disclosure and process memory corruption. |
| CVE-2025-38137 | `linux-libc-dev` | Patch pending | Use-after-free race condition in kernel PCI power control during rescan unregistration, leading to potential denial of service or privilege escalation. |
| CVE-2025-38187 | `linux-libc-dev` | Patch pending | Use-after-free vulnerability in nouveau display driver RPC container handling. |
| CVE-2025-38204 | `linux-libc-dev` | Patch pending | Array index out-of-bounds read in JFS filesystem index calculation triggering memory access violations. |
| CVE-2025-38206 | `linux-libc-dev` | Patch pending | Double-free condition in exFAT filesystem delayed free pathway causing kernel crash / denial of service. |
| CVE-2025-38421 | `linux-libc-dev` | Patch pending | Double-free flaw in AMD Platform Management Framework device allocation handling. |

---

## Python-Specific Vulnerabilities

The container environment contains two direct high-severity Python package vulnerabilities that pose direct threats to AI model distribution and execution:

### 1. `wheel` (v0.45.1) — CVE-2026-24049 (HIGH)
- **Vulnerability:** Arbitrary Code Execution and File Permission Tampering.
- **Mechanism:** In versions `0.40.0` through `0.46.1`, the wheel unpacking utility fails to sanitize archive file permissions and target paths during extraction. If a developer or automated CI/CD pipeline installs a malicious third-party wheel dependency (e.g. via dependency confusion or typosquatting), the unpacker can overwrite critical system binaries.
- **Fixed In:** Upgrade `wheel` to `>= 0.46.2`.

### 2. `jaraco.context` (v5.3.0) — CVE-2026-23949 (HIGH)
- **Vulnerability:** Path Traversal (Zip Slip) via Tarball Extraction.
- **Mechanism:** The `jaraco.context.tarball()` context manager does not validate member filenames against target base directories before extraction, allowing archive entries with relative directory traversal sequences (`../../`) to write files into arbitrary system locations.
- **Fixed In:** Upgrade `jaraco.context` to `>= 6.1.0`.

---

## Dockerfile Issues

Static analysis of `Dockerfile` identified 6 critical container security flaws:

### 1. Missing USER Directive (Running as Root) — HIGH

**Risk:** The container does not declare a `USER` instruction, defaulting execution to `root` (UID 0). In the event of a container breakout, remote code execution (e.g., via prompt injection tool-use or CVE-2026-24049 wheel unpack), an attacker gains immediate root-level capabilities on the container and potentially the host kernel.  
**Fix:** Create a dedicated unprivileged user and switch to it before launching the application:
```dockerfile
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser
USER appuser
```

### 2. Unpinned Base Image Digest — MEDIUM

**Risk:** The directive `FROM python:3.11-slim` relies on a mutable tag. New upstream pushes to Docker Hub can introduce breaking dependency changes, unvetted binaries, or compromised upstream layers without build verification.  
**Fix:** Pin the base image to an immutable cryptographic SHA256 digest:
```dockerfile
FROM python:3.11-slim@sha256:d8a57e62a98f1f77d3f82cf0fbfaab7f29bb467554b5dfd1e67cf7df13b28b78
```

### 3. Overly Broad COPY . Context — MEDIUM

**Risk:** The instruction `COPY . /app` copies the entire repository into the container image. This risks accidentally bundling secrets, `.env` files with API keys (`OPENAI_API_KEY`), `.git` repositories containing commit history, training artifacts, and local scratch files into production layers.  
**Fix:** Implement a strict `.dockerignore` file and copy only essential production directories:
```dockerfile
COPY classifier /app/classifier
COPY rag_chatbot /app/rag_chatbot
COPY requirements.txt /app/requirements.txt
```

### 4. Missing HEALTHCHECK Instruction — LOW

**Risk:** The container lacks a `HEALTHCHECK` contract. Container orchestration platforms (Docker Swarm, Kubernetes, ECS) cannot automatically detect if the Flask HTTP process hangs, deadlocks, or becomes unresponsive.  
**Fix:** Add an active health monitoring probe targeting the application health endpoint:
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1
```

### 5. Build Tools Retained in Production (`gcc`, `build-essential`) — MEDIUM

**Risk:** The image retains C compilers, linkers, and build utilities (`gcc`, `build-essential`, `python3-dev`). While required for compiling native C-extensions like FAISS or PyTorch, retaining compilers in production images significantly lowers the barrier for attackers to compile privilege escalation exploits in memory.  
**Fix:** Adopt a multi-stage Docker build pattern. Compile wheels in a `builder` stage, then copy only compiled wheels and runtime shared libraries into a clean, compiler-free production runtime stage.

### 6. Unnecessary Network/VCS Utilities in Production (`curl`, `git`) — LOW

**Risk:** Retaining network diagnostic tools and version control binaries (`curl`, `git`) facilitates post-exploitation lateral movement, allowing adversaries to download secondary attack stages or exfiltrate corporate IP directly from the container.  
**Fix:** Remove `git` and `curl` from the final production stage, relying on internal Python health endpoints or standard minimal base images (e.g. distroless).

---

## AI Pipeline Risk Assessment

Supply chain vulnerabilities in AI/ML architectures present unique threat vectors beyond traditional software systems:

1. **Model Checkpoint & Wheel Integrity:** AI pipelines rely heavily on external package repositories (PyPI, Hugging Face) and pre-trained model weights (`.pt`, `.bin`). Vulnerabilities such as `CVE-2026-24049` (wheel code execution) can be exploited to replace model weights or inject backdoor hooks during automated package installations.
2. **Container Privilege vs. GPU/Host Exposure:** Running AI inference workloads as root increases the blast radius of container escapes. If an adversary compromises the RAG chatbot via application-level RCE, root container privileges enable access to underlying GPU drivers, mounted Cloud Storage buckets, and shared memory volumes.
3. **Secret Disclosure via Image Layers:** Machine learning deployments frequently require API credentials for external foundation models (e.g., OpenAI, Anthropic). Broad `COPY .` operations capture local `.env` files into image layer metadata, exposing API keys to anyone with image pull permissions.

---

## Remediation Priority

| Priority | Action | Target Component | Justification |
|----------|--------|------------------|---------------|
| **1 (Immediate)** | Enforce non-root execution (`USER appuser`) and implement `.dockerignore` | `Dockerfile` | Eliminates root privilege escalation risk and prevents leakage of API keys/secrets into image layers. |
| **2 (Immediate)** | Upgrade `wheel` (>=0.46.2) and `jaraco.context` (>=6.1.0) | `requirements.txt` | Remediates active high-severity Python code execution and path traversal vulnerabilities. |
| **3 (Near-term)** | Refactor build pipeline to multi-stage Docker build | Build Pipeline | Strips `gcc`, `build-essential`, and package managers from runtime, reducing attack surface and eliminating 700+ OS vulnerabilities. |
| **4 (Near-term)** | Pin base image to immutable SHA256 digest | `Dockerfile` | Guarantees deterministic, tamper-proof builds and prevents upstream supply chain poisoning. |
| **5 (Medium-term)** | Integrate container vulnerability scanning (Trivy/Snyk) into CI/CD | DevSecOps Pipeline | Blocks deployment of images containing unresolved HIGH or CRITICAL CVEs automatically. |
