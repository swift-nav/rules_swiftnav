#include <iostream>
#include <limits>

int main()
{
    if (std::numeric_limits<double>::is_iec559)
    {
        std::cout << "IEC 559 (IEEE 754) doubles supported." << std::endl;
        return 0;
    }
    else
    {
        std::cerr << "IEC 559 (IEEE 754) doubles not supported." << std::endl;
        return 1;
    }
}
