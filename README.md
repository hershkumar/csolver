# csolver
A (small-order) quantum circuit generator. Uses the universal gate set of arbitrarily controlled CNOT gates (NOT, CNOT, CCNOT, etc) for generation of reversible quantum circuits.

# How to Use csolver
csolver takes in a truth table in a csv file (for example `examples/2input.csv` or `examples/3input.csv`) and generates a circuit drawing and gate counts to a output text file (`2output.txt` and `3output.txt` respectively). 
## Dependencies
csolver relies on the Microsoft Z3 Theorem Prover, which can be installed via `pip`:
```bash
pip3 install z3-solver
```

## Running csolver
csolver takes 3 commandline arguments, the first being the input csv file with the truth table, the second being the number of gates that the circuit should use, and the final argument being the output file name:

```bash
python3 csolver.py examples/2input.csv 8 examples/2output.txt
```

# Methodology
csolver encodes the possible existence of a circuit that fulfils the truth table as a SAT problem, which can then be solved via the Z3 SAT solver. This is done via the addition of constraints to the SAT problem. There are sets of variables that need to be tracked in order to encode the existence of a circuit:

1. `c_i_j` represents whether the `i`th gate is controlled on the `j`th bit.
2. `v_i_j` represents the output of the `i`th gate on the `j`th set of inputs
3. `n_i` represents whether there is an initial `NOT` gate on the `i`th bit.

With these sets of variables, we can encode the 3 sets of clauses that govern circuits.

1. Gates cannot be controlled on bits that are higher than them (or be controlled on themselves)
2. For a circuit with `n` output bits, the outputs of the last `n` gates must match the outputs in the truth table
3. The output of any given gate relies on the outputs of the gates on the bits it is controlled on, and the initial value of the bit it acts on.

With these clauses, we can hand the system over to z3, which can then provide the output of the variables `c_i_j` and `n_i`, which can then be parsed into a circuit drawing. The drawing is then analyzed to compute the number of each type of gate in use.

Note that csolver will always find circuits with a diagonal of arbitrary controlled NOT gates, with singular initial NOT gates on each bit, and csolver will use ancillary bits, as it only generates circuits with one gate per bit.

## Future Improvements
- Look into reducing the overhead used by the python bindings for z3, perhaps port over to c++ for performance benefits
- Look into circuit simplification tools/algorithms to decreased qubit and/or entangling gate costs.