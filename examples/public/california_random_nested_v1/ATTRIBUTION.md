# California Housing: source and reuse

Liu, Nelson (2016). *scikit-learn california housing dataset cal_housing.tgz*. Figshare, version 2. https://doi.org/10.6084/m9.figshare.3829992.v2

The Figshare record identifies file 5976036 (441,963 bytes) and labels it CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. The downloaded archive's SHA-256 matches the checksum shipped with scikit-learn. The complete public metadata response is retained in expected/figshare_metadata.json. The archive contains a numeric data file and domain description; neither adds a conflicting restriction.

Original research: Pace, R. Kelley, and Ronald Barry (1997). Sparse Spatial Autoregressions. *Statistics & Probability Letters*, 33, 291–297. https://doi.org/10.1016/S0167-7152(96)00140-X. The data derive from the 1990 US census, with one row per block group.

This package transforms source totals to scikit-learn's eight predictors and scales median house value to units of USD100,000. The transformation and hashes are specified in expected/provenance.json and tools/cases/prepare_california.py. No row is removed; source order and capped target values are retained. Data authors and depositors do not endorse PsyML or this validation.

These historical random-fold scores are a software-conformance example. They do not measure out-of-region transfer, current market value, causality or suitability for lending/housing decisions.
