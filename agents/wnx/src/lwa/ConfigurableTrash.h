// SPECIAL INCLUDE FOR Configurable.h
#ifndef ConfigurableTrash_h__
#define ConfigurableTrash_h__

    virtual void output(const std::string &key,
                        std::ostream &out) const override {
        for (const auto & [var, value] : this->values()) {
            out << key << " " << var << " = " << value << "\n";
        }
    }
#endif  // ConfigurableTrash_h__
