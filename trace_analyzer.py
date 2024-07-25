#!/usr/bin/env python3
import json, sys

class BasicBlock:
    def __init__(self, address=0, is_internal=True, label=""):
        self.address = address
        self.finish_address = address
        self.instructions = []
        self.prev_blocks = set()
        self.next_blocks = set()
        self.is_internal = is_internal
        self.label = label
        self.is_complete = False

def expand_block_address(address):
    tail = hex(address)[2:]
    return (16-len(tail))*'0' + tail

def get_split_idx(block, address):
    idx = 0
    base_addr = block.address
    for pair in block.instructions:
        if base_addr == address:
            return idx
        base_addr += pair[1]
        idx += 1

def export_to_dot(block_set, filename):

    with open(filename, mode='w', encoding='utf-8') as dot_file:
        dot_file.write("strict digraph {\n")

        for block in block_set: 

            vertice_metainfo = ""
            if block.is_internal:

                label_title = expand_block_address(block.address)
                vertice_metainfo += f"\"{label_title}\" " + \
                    f"[ shape = box, label = \"{label_title}\\n"

                if len(block.instructions) == 1:
                    vertice_metainfo += f"{block.instructions[0][0]}\", "

                elif len(block.instructions) == 2:
                    vertice_metainfo += f"{block.instructions[0][0]}\\n" + \
                        f"{block.instructions[1][0]}\", "

                elif len(block.instructions) > 2:
                    vertice_metainfo += f"{block.instructions[0][0]}\\n" + \
                        f"...\\n{block.instructions[-1][0]}\", "

                else:
                    vertice_metainfo += "\", "

                vertice_metainfo += "color = \"#c5d6e0\","

            # external call case
            else:
                label_title = block.label
                vertice_metainfo += f"\"{label_title}\" " + \
                    f"[ label = \"{label_title}\", color = \"#aff283\","

            vertice_metainfo += " style = filled ]"
            dot_file.write(vertice_metainfo + '\n')

            for successor in block.next_blocks:
                if successor.is_internal:
                    dot_file.write(f"\"{label_title}\" -> " + \
                        f"\"{expand_block_address(successor.address)}\"\n")
                else:
                    dot_file.write(f"\"{label_title}\" -> " + \
                        f"\"{successor.label}\"\n")

        dot_file.write("}\n")


args = sys.argv
help_message = "Usage: ./<script> <path to input JSON file> <output file name>"
if len(args) != 3:
    print(help_message)
    sys.exit()

initial_block = None
block_set = set()
foreign_blocks = set()
with open(args[1]) as json_stream:

    trace = json.load(json_stream)

    cur_block = None
    branch_detected = False
    foreign_branch_detected = False
    foreign_name = ""
    for line in trace:

        address = line['address']
        text = line['text']
        hex_dump = line['hexDump']

        if not initial_block:
            initial_block = BasicBlock(address)
            block_set.add(initial_block)
            cur_block = initial_block

        if branch_detected:

            if foreign_branch_detected:
                found = None
                for fb in foreign_blocks:
                    if fb.label == foreign_name:
                        found = fb
                        break

                # need to create a new foreign block
                if found is None:
                    intermediate_call_block = BasicBlock(
                        is_internal=False, label=foreign_name)
                    intermediate_call_block.is_complete = True
                    foreign_blocks.add(intermediate_call_block)

                else:
                    intermediate_call_block = found

                cur_block.next_blocks.add(intermediate_call_block)
                intermediate_call_block.prev_blocks.add(cur_block)

            next_block = None
            in_middle_jump = False
            for block in block_set:
                if block.address <= address <= block.finish_address:

                    if address == block.address:
                        next_block = block
                    else:
                        in_middle_jump = True
                        next_block = BasicBlock(address)
                        block_set.add(next_block)
                        split_idx = get_split_idx(block, address)
                        next_block.instructions = \
                            block.instructions.copy()[split_idx:]
                        block.instructions = block.instructions[:split_idx]
                        next_block.next_blocks = block.next_blocks.copy()
                        block.next_blocks.clear()
                        block.next_blocks.add(next_block)
                        next_block.prev_blocks.add(block)
                        next_block.finish_address = block.finish_address
                        next_block.is_complete = True
                        block.finish_address = address - \
                            block.instructions[-1][1]

                    break

            if next_block is None:
                next_block = BasicBlock(address)
                block_set.add(next_block)

            if foreign_branch_detected:
                intermediate_call_block.next_blocks.add(next_block)
                next_block.prev_blocks.add(intermediate_call_block)
            else:
                cur_block.next_blocks.add(next_block)
                if not in_middle_jump:
                    next_block.prev_blocks.add(cur_block)

            cur_block = next_block

            # flushing data due to processing being completed
            branch_detected = False
            foreign_branch_detected = False
            foreign_name = ""

        if cur_block.is_complete:
            if not (cur_block.address <= address <= cur_block.finish_address):
                for successor in cur_block.next_blocks:
                    if address == successor.address:
                        cur_block = successor
                        break

        # block has not been filled with instructions yet so it needs to be
        if not cur_block.is_complete:
            cur_block.instructions.append((text, len(hex_dump)/2))

        if 'isBranch' in line and line['isBranch'] is True:

            branch_detected = True
            cur_block.finish_address = address
            cur_block.is_complete = True
            if 'isForeignBranch' and 'foreignTargetAddress' \
                and 'foreignTargetName' in line:
                
                foreign_branch_detected = True
                foreign_name = line['foreignTargetName']


print("Internal blocks:    ", len(block_set))
print("Foreign blocks:     ", len(foreign_blocks))
block_set = block_set.union(foreign_blocks)
export_to_dot(block_set, args[2])