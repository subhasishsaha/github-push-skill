# Open Source & Software License Selection Guide

Selecting the appropriate license is an essential step before publishing any repository to GitHub or another public/private code hosting service.

## The Default State (No License)

> [!WARNING]
> If a repository has no `LICENSE` file, the code defaults to **Exclusive Copyright / All Rights Reserved** under international copyright law. Other developers can view the code if public, but they have no legal right to copy, modify, distribute, or incorporate it into their own projects.

---

## License Comparison Matrix

| License | SPDX Identifier | Category | Commercial Use | Modification | Distribution | Disclose Source Required? |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **MIT** | `MIT` | Permissive | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Apache 2.0** | `Apache-2.0` | Permissive + Patent Grant | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **BSD 3-Clause** | `BSD-3-Clause` | Permissive | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Mozilla Public License 2.0** | `MPL-2.0` | Weak Copyleft (File-level) | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Modified files only |
| **GNU GPL v3** | `GPL-3.0-only` | Strong Copyleft | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Entire derivative work |
| **GNU AGPL v3** | `AGPL-3.0-only` | Network Copyleft | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Yes (including network access) |
| **Unlicense** | `Unlicense` | Public Domain | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Proprietary** | `LicenseRef-Proprietary` | Closed / Commercial | ❌ By Permission | ❌ By Permission | ❌ By Permission | N/A |

---

## When to Choose Which License

### 1. MIT License
- **Best for:** Maximum adoption, utilities, libraries, CLI tools, frontend components, and educational templates.
- **Why:** Extremely short, well-understood by enterprise legal teams, allows anyone to use, modify, and distribute with minimal restriction.
- **Obligation:** Keep the copyright notice and permission notice in copies.

### 2. Apache 2.0 License
- **Best for:** Enterprise frameworks, multi-contributor projects, cloud infrastructure, AI models, and SDKs.
- **Why:** Includes explicit patent grants from contributors and protects contributors against patent infringement claims.
- **Obligation:** Retain copyright, license, notices, and state changes made to files.

### 3. BSD 3-Clause
- **Best for:** Academic software, algorithms, scientific computing (NumPy, SciPy, BSD OS).
- **Why:** Similar to MIT but includes a specific clause prohibiting using names of contributors to endorse derivative products without permission.

### 4. GNU GPL v3 / AGPL v3 (Copyleft)
- **Best for:** Preserving open-source freedom and preventing proprietary commercial forks without shared improvements.
- **AGPL v3** specifically closes the "SaaS loophole" — anyone running your modified code over a network must provide source code to users.

### 5. Proprietary / All Rights Reserved
- **Best for:** Commercial products, internal company repositories, closed-source SaaS backends.
- **Statement:** `Copyright (c) [Year] [Owner]. All Rights Reserved.`

---

## Official Resources

- [choosealicense.com](https://choosealicense.com/) (Maintained by GitHub)
- [spdx.org/licenses](https://spdx.org/licenses/) (SPDX License List)
- [opensource.org/licenses](https://opensource.org/licenses) (Open Source Initiative)
