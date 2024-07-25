#include "pin.H"
#include <iostream>
#include <unistd.h>
#include <stdio.h>

FILE *output;

INT32 Usage() {

    cerr <<
        "This tool gets the key generating metadata from \"encrypt\" binary "
        "and places it in \"encrypt.key\"\n";
    cerr << KNOB_BASE::StringKnobSummary();
    cerr << endl;
    return -1;
}

VOID ArgDumper(ADDRINT second, ADDRINT third) {

    unsigned char *buf = (unsigned char *) third;

    for (unsigned int i = 0; i < second; ++i)
        fprintf(output, "%c", buf[i]);
}

VOID Image(IMG img, VOID *v) {

    RTN bf_set_key_rtn = RTN_FindByName(img, "BF_set_key");
    if (RTN_Valid(bf_set_key_rtn)) {

        printf("%s is a valid routine\n", RTN_Name(bf_set_key_rtn).c_str());
        RTN_Open(bf_set_key_rtn);
        RTN_InsertCall(bf_set_key_rtn, IPOINT_BEFORE, (AFUNPTR) ArgDumper, 
            IARG_FUNCARG_ENTRYPOINT_VALUE, 1, IARG_FUNCARG_ENTRYPOINT_VALUE, 2, 
            IARG_END);
        RTN_Close(bf_set_key_rtn);
    }
}

VOID Fini(INT32 code, VOID *v) {}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char *argv[]) {

    // initializing symbol table code
    PIN_InitSymbols();

    if(PIN_Init(argc,argv)) {
        return Usage();
    }
    
    output = fopen("encrypt.key", "w");
    //INS_AddInstrumentFunction(Instruction, 0);
    IMG_AddInstrumentFunction(Image, 0);
    PIN_AddFiniFunction(Fini, 0);

    // Never returns
    PIN_StartProgram();   
    return 0;
}
