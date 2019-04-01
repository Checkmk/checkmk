#include <memory>
#include "Column.h"
#include "OffsetStringHostMacroColumn.h"
#include "Row.h"
#include "gtest/gtest.h"
#include "nagios.h"

TEST(OffsetStringHostMacroColumn, simple) {
    // Backwards you must build the list, my young padawan...
    customvariablesmember cvm1{const_cast<char *>("HARRY"),
                               const_cast<char *>("HIRSCH"), 0, nullptr};
    customvariablesmember cvm2{const_cast<char *>("ERNIE"),
                               const_cast<char *>("BERT"), 0, &cvm1};
    customvariablesmember *custom_variables = &cvm2;
    Row row{&custom_variables};

    OffsetStringHostMacroColumn oshmc("funny_column_name", "Cool description!",
                                      -1, -1, -1, nullptr, 0);

    EXPECT_EQ("funny_column_name", oshmc.name());
    EXPECT_EQ("Cool description!", oshmc.description());
    EXPECT_EQ(&custom_variables, oshmc.columnData<void>(row));
    EXPECT_EQ(ColumnType::string, oshmc.type());

    auto cvm = *oshmc.columnData<const customvariablesmember *const>(row);
    EXPECT_STREQ("ERNIE", cvm->variable_name);
    EXPECT_STREQ("BERT", cvm->variable_value);

    cvm = cvm->next;
    EXPECT_STREQ("HARRY", cvm->variable_name);
    EXPECT_STREQ("HIRSCH", cvm->variable_value);

    cvm = cvm->next;
    EXPECT_EQ(nullptr, cvm);
}
