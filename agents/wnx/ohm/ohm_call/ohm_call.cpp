// ohm_call.cpp : This file contains the 'main' function. Program execution
// begins and ends there.
//

#pragma managed

#include <iostream>
using namespace System;
using namespace Bridge;

namespace wrapper {

public
ref class ManagedCall {
public:
    Bridge::Main ^ start() {
        Bridge::Main ^ m = gcnew Bridge::Main();
        m->Start();
        return m;
    };
};
}  // namespace wrapper

int main() {
    wrapper::ManagedCall managed_caller;
    Bridge::Main ^ m = managed_caller.start();
    m->Stop();
}
