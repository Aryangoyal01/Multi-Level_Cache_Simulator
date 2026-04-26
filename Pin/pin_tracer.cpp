#include "pin.H"

#include <fstream>
#include <iostream>
#include <string>

using std::cerr;
using std::endl;
using std::hex;
using std::ofstream;
using std::string;

// Output trace file path. Each line is: "R 0x..." or "W 0x...".
KNOB<string> KnobOutputFile(
    KNOB_MODE_WRITEONCE,
    "pintool",
    "o",
    "pin_tracer.out",
    "memory trace output file"
);

static ofstream traceFile;

VOID RecordMemRead(VOID* addr) {
    traceFile << "R " << std::showbase << hex << reinterpret_cast<ADDRINT>(addr) << endl;
}

VOID RecordMemWrite(VOID* addr) {
    traceFile << "W " << std::showbase << hex << reinterpret_cast<ADDRINT>(addr) << endl;
}

VOID InstrumentInstruction(INS ins, VOID* v) {
    UINT32 memOps = INS_MemoryOperandCount(ins);

    for (UINT32 i = 0; i < memOps; i++) {
        if (INS_MemoryOperandIsRead(ins, i)) {
            INS_InsertPredicatedCall(ins, IPOINT_BEFORE, AFUNPTR(RecordMemRead),
                                     IARG_MEMORYOP_EA, i,
                                     IARG_END);
        }

        if (INS_MemoryOperandIsWritten(ins, i)) {
            INS_InsertPredicatedCall(ins, IPOINT_BEFORE, AFUNPTR(RecordMemWrite),
                                     IARG_MEMORYOP_EA, i,
                                     IARG_END);
        }
    }
}

VOID Fini(INT32 code, VOID* v) {
    traceFile << "#eof" << endl;
    traceFile.close();
}

INT32 Usage() {
    cerr << "PIN memory tracer" << endl;
    cerr << KNOB_BASE::StringKnobSummary() << endl;
    return 1;
}

int main(int argc, char* argv[]) {
    if (PIN_Init(argc, argv)) {
        return Usage();
    }

    traceFile.open(KnobOutputFile.Value().c_str());
    if (!traceFile.is_open()) {
        cerr << "Failed to open trace output file: " << KnobOutputFile.Value() << endl;
        return 1;
    }

    INS_AddInstrumentFunction(InstrumentInstruction, nullptr);
    PIN_AddFiniFunction(Fini, nullptr);

    PIN_StartProgram();
    return 0;
}
