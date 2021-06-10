# csolver.py, Hersh Kumar, June 2021

# A rewritten version of my circuit finding code from 2019,
# made to work on more truth tables (more than just 2 outputs)
# Output of the program has also been beautified,
# making it easier to generate the circuit from output.
# The circuit finder uses ancillary qubits/bits, and thus provides a
# circuit that satisfies the table, not a simplfied circuit
# using minimal qubits/bits or gates.
# The finder uses the Microsoft Z3 SMT solver to solve the SAT
# problem.

# Input: This program reads from a csv file (first arg)
# and also takes in the number of gates that the circuit should use
# (second cmdline arg)
# The output is stored in a file (default name output.txt), which
# can be changed via the third cmdline arg (a filename)

# Truth table format:
# first element of row is the binary representation of the input values
# second and all elements after are values of the output bits
# for example:

# 000,1,1
# 001,1,0
# 010,1,0
# 011,0,1
# 100,1,1
# 101,0,0
# 110,1,1
# 111,1,0
# where the first column is the input values, and the last two
# columns are the values of the output bits

from z3 import *
import sys
import math
import pandas as pd
import os.path
import time

# symbols to use for drawing the circuit to the file
CONTROL_DOT = "o"
NOT_GATE = "X"
PIPE = "|"


# solves for the circuit given by the truth table in filename
# using num_gates gates/bits 
def solve_table(filename, num_gates, out_file):
    s = Solver()
    # first read in from the filename, store the truth table in a 2d array
    # disregard the first column (we can get input from row number to binary)
    print("Reading csv File...")
    truth_table = pd.read_csv(filename, header=None).iloc[:,1:]
    truth_table = truth_table.to_numpy()
    num_gates = int(num_gates)

    num_rows = len(truth_table)
    num_cols = len(truth_table[0])
    
    # convert all the elements into integers
    for i in range(num_rows):
        for j in range(num_cols):
            truth_table[i][j] = int(truth_table[i][j])
    # number of output bits is just the length of the inner array
    num_output_bits = num_cols
    # number of input bits is the number of bits necessary to represent
    # however many rows there are
    num_input_bits = math.ceil(math.log2(num_rows)) 
    
    print("Setting up arrays...")
    # make the c two dimensional array
    c = []
    for i in range(num_gates):
        c.append([])
        for j in range(num_gates):
            c[i].append(Bool("c_"+str(i)+"_"+str(j)))

    # Now for the array v, also 2d
    v = []
    for i in range(num_gates):
        v.append([])
        for j in range(num_rows):
            v[i].append(Bool("v_" + str(i) + "_" + str(j)))

    # and the n array
    n = []
    for i in range(num_gates):
        n.append(Bool("n_"+str(i)))

    print("Adding constraints...\n")
    # Now to add the constraints to the system
    # gates cannot be controlled on gates that are above them, or themselves
    for i in range(num_gates):
        for j in range(i, num_gates):
            s.add(c[i][j] == False)
    

    # Now the output bits must math the truth table. The value of the output bits is
    # just the output of the last n gates, where n is the number of output bits
    # Loop through the last num_output_bits gates, and make sure their outputs match
    for gate in range(num_gates - num_output_bits, num_gates):
        for inp in range(num_rows):
            # check the table to see what the output of the correct
            # output bit is for the given input
            table_out = truth_table[inp][gate - (num_gates - num_output_bits)]
            if (table_out == 0):
                s.add(v[gate][inp] == False)
            else:
                s.add(v[gate][inp] == True)

    # gate evolution clause
    # this is the most complicated of the clauses
    # defines the output of a certain gate to be based on whether there is a prior
    # not on the bit, as well as the values of all bits preceding it
    # where we filter the ones that have controls on them
    # in boolean form:
    # v[i][t] = n[i] xor ((v[i-1][t] or not c[i][i-1]) and (v[i-2][t] or not c[i][i-2]) and  ... and (v[0][t] or not c[i][0]))
    
    # for every gate
    for i in range(num_gates):
        # for every input
        for inp in range(num_rows):
            # start with the existence of the not
            clause = n[i]
            temp = True
            #loop through all gates below it
            for count in range(1, i + 1):
                temp = And(temp, Or(v[i-count][inp], Not(c[i][i-count])))

            clause = Xor(clause, temp)
            # now we make sure that the input values are correctly set
            if i < num_input_bits:
                input_val = False
                if (bin(inp)[2:].zfill(num_input_bits)[i] == '1'):
                    input_val = True
                clause = Xor(clause, input_val)

            s.add(v[i][inp] == clause)

    
    print("Checking satisfiability...\n")
    # Now that all clauses have been input, we can use z3 to solve the model
    if (s.check() == sat):
        print("Model is satisfiable!")
        model = s.model()
        output_file = open(out_file, "w+")
        #print(s.assertions())
        for d in model:
            if str(model[d]) == "True" and not "v" in str(d):
                output_file.write(str(d) + "\n")
        output_file.close()
    # if the system isn't satisfiable
    else:
        print("Model is not satisfiable")
        return (False, 0, 0)
    return (True, num_input_bits, num_output_bits)

# draws the generated circuit from the output of the truth table solver
# circuit is drawn into the outfile, and labels the input, ancilla,
# and output bits. It also computes the gate counts used in the circuit. 
def draw_circ(infile, outfile, num_in, num_out):
    #read in the lines
    with open(infile) as f:
        data = f.read().splitlines()
    data.sort()
    nots = [i for i in data if i[0] == 'n']
    cs = [i for i in data if i[0] == 'c']

    # the circuit is always nxn where n is the max seen in the c's
    # lets find the maximum
    parsed_cs = [int(i.split('_')[1]) for i in cs]
    parsed_all = [int(i.split('_')[1]) for i in data]

    n = max(parsed_all) + 1  
    #make a matrix to represent it
    circ = [["-" for i in range(n)] for j in range(n)]

    # do the nots first
    for i in range(len(nots)):
        parsed_not = int(nots[i].split('_')[1])
        circ[parsed_not][0] = NOT_GATE

    # do the diagonal
    for i in range(n):
        for j in range(n):
            if (i==j):
                circ[i][j] = NOT_GATE


    # and now the control dots
    for i in range(len(cs)):
        x = int(cs[i].split('_')[1])
        y = int(cs[i].split('_')[2])
        circ[y][x] = CONTROL_DOT

    # finally, the pipes between the dots and the nots
    for i in range(1, n):
        for j in range(1,i):
            if (circ[j][i] == "-"):
                # now check if there are any 'o's above the current cell
                if (o_above(circ, j, i)):
                    circ[j][i] = PIPE

    # now write the matrix to the outfile
    f = open(outfile, "w")
    for i in range(n):
        # if its an input bit or output bit we denote it
        if (i < num_in):
            f.write("|i> ")
        elif (i >= (n - num_out)):
            f.write("|o> ")
        else:
            f.write("|a> ")
        # write out the matrix with spacers
        for j in range(n):
            f.write("-")
            f.write(circ[i][j])
            f.write("-")
        f.write("\n")

    f.write("\n\n")
    # now write out the gate counts in order
    f.write("===Gate Counts====\n")
    # compute the number of C^n NOT gates in the circuit
    # loop through the matrix starting at 1, and count the number of o's
    # in the column which tells what gate it is
    gate_dict = {}
    for i in range(1,n):
        num_os = 0
        for j in range(n):
            if (circ[j][i] == CONTROL_DOT):
                num_os += 1
            
        # now we have the number of controls in the gate, so we know what gate it is
        # n controls make it a C^nNot gate
        gate_name = ("C" * num_os) + "NOT"
        
        # add to the dictionary
        if (gate_name in gate_dict):
            gate_dict[gate_name] = gate_dict[gate_name] + 1
        else:
            gate_dict[gate_name] = 1

    # add the not gates we already have in the first column
    if ("NOT" in gate_dict):
        gate_dict["NOT"] = gate_dict["NOT"] + len(nots)
    else:
        gate_dict["NOT"] = len(nots)
    # sort it by occurrences
    sorted_list = sorted(gate_dict.items(), key=lambda x: x[1], reverse=True)
    # write them to the file
    for pair in sorted_list:
        f.write(pair[0] + " gates: " + str(pair[1]) + "\n")

    print("Drawn circuit to file.")
    f.close()

# checks if there is a control dot anywhere above the given cell
# helper method for the draw_circ function
def o_above(circ, j, i):
    for y in range(0, j):
        if circ[y][i] == CONTROL_DOT:
            return True
    return False

# runs the table solver and drawing, based on command line arguments
def main():
    if (len(sys.argv) == 4):
        filename = sys.argv[1]
        num_gates = sys.argv[2]
        out_file = sys.argv[3]

        # check if the input file exists and is a csv
        if os.path.isfile(filename):
            if filename.endswith('.csv'):
                start_time = time.time()
                
                (ret, num_in, num_out) = solve_table(filename, num_gates, out_file)
                
                end_time = time.time()
                
                elapsed_time = end_time - start_time
                print("Time elapsed: " + str(elapsed_time) + " seconds.")
                
                if (ret):
                    print("Drawing circuit to file...")
                    draw_circ(out_file, out_file, num_in, num_out)
            else:
                print("Please input a .csv file.")
        else:
            print("That file does not exist.")
    else:
        print("Please input the correct number of arguments.")
    


if __name__ == '__main__':
    main()