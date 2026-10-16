# Revision 3 validation record

Local manuscript validation date: 2026-10-15. Repository synchronization checks
were repeated on 2026-10-16. Numerical reconstruction was checked with CPython
3.9.23 and 3.13.13; import checks used Python 3.9.23 and Matplotlib 3.9.4.

- Every archived planning objective was re-evaluated after configuration mapping.
  Maximum absolute deviation was 3.637978807091713e-12 for gear and
  1.1368683772161603e-13 for Mk04, below the 1e-6 acceptance tolerance.
- The main comparison's six representative points agree with the manuscript at
  displayed precision. Multiset C1>BASE is 1/0 (gear) and
  0.8160919540229885/0 (Mk04), with reverse direction shown after the slash.
- The four archived-candidate pools select identical source IDs at 0 and 0.08.
  The complete candidate and per-run records are in pricepool_gear_rev3.json.
- Degradation self-check passed on gear and Mk01, 200 chromosomes each, with
  maximum deviation zero. The test's source-root import path was repaired.
- Existing critical-path bound check passed.
- The two historical runner --check commands imported successfully and created
  the results directory without starting optimization.
- No new evolutionary search was run. The core fjsp/*.py model and algorithm
  files are byte-identical to public commit 81cdfd8.
- table2_repro.json contains ten higher NSGA-II mean-HV comparisons against
  ASA-fix, and six C(NSGA-II>ASA-fix) values equal to one. These are checks of
  supplied historical summary records, not a fresh 20-run reproduction.

The manuscript was rendered with Microsoft Word, and every page inspected.
The response document was also rendered and checked. Original input documents
were not overwritten. Author affiliation and correspondence placeholders remain.

For the repository synchronization, numerical reconstruction, degradation and
critical-path checks, and both historical runner import checks passed again in
a fresh checkout. Repository text uses LF line endings; reconstruction writes
platform-independent UTF-8 line endings. CPython 3.13 reconstruction matches
the delivered numerical JSON values; Python 3.9 differs at floating-point
roundoff level (about 1e-12), within the 1e-6 verification tolerance. Result
file hashes are environment-specific. The DOCX and ZIP files retain their
original delivery hashes. The root manifest covers the repository snapshot;
the ZIP retains its separate original manifest.
