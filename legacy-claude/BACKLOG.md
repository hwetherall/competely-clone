# Project Backlog & Strategic Improvements

## 1. AI Hallucination & Context Leakage
- **Observation:** In a run with {Uber, Lyft, DiDi, Gojek}, the generated rationale for "Super-App Service Ecosystem" mentioned **Grab**, which was not in the input set.
- **Root Cause:** The model (Kimi k2.5) likely associates Gojek strongly with Grab due to training data (Southeast Asia ride-hailing duopoly) and "completed the pattern" despite the specific prompt constraints.
- **Proposed Fixes:**
    - **Strict Constraint Prompting:** Add negative constraints to the prompt: *"Do NOT mention companies that are not in the provided Set of Competitors."*
    - **Post-Processing Filter:** A simple string check to flag or remove company names that aren't in the input list (fuzzy matching might be needed).

## 2. Data Availability & Company Maturity Strategy
- **Observation:** The current pipeline works exceptionally well for massive public companies (Uber, Lyft) with abundant public data (10-Ks, news, analyst reports).
- **Challenge:** For early-stage (Series A, Pre-revenue) or private companies, this approach might fail or hallucinate due to lack of data.
- **Proposed Solution (Adaptive Pipeline):**
    - **Pre-flight Check:** Before generating parameters, run a quick "Data Density Check" on the companies.
    - **Branching Logic:**
        - **High Density (Public):** Use current deep-dive strategy (Analyst reports, financial metrics).
        - **Low Density (Private/Startup):** Switch to "Inference Mode." Focus on:
            - Founders' backgrounds (LinkedIn/Twitter).
            - Product demos/screenshots (Visual analysis).
            - Job postings (Inferring tech stack/growth areas).
            - Customer reviews (G2/Capterra) rather than financial reports.
    - **User Flag:** Allow user to toggle "Early Stage Mode" to force this behavior.
