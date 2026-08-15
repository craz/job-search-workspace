# Instructions for workspace scripts

1. Use Python 3.12 standard library unless a dependency has a demonstrated need.
2. Document module role, control flow, inputs, outputs, side effects, failures,
   invariants and safety guarantees; a one-line placeholder docstring is invalid.
3. Keep subprocesses non-interactive and bounded where they can wait on network
   or credentials. Never reset, clean or overwrite an existing checkout.
4. Add unit coverage for validation/failure behavior and update Make interfaces.
5. Run `python3 -m compileall`, relevant unit/BDD tests and `git diff --check`.

