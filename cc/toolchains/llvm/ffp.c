#include <stdio.h>

static const double
half =  5.00000000000000000000e-01, /* 0x3FE00000, 0x00000000 */
S1  = -1.66666666666666324348e-01, /* 0xBFC55555, 0x55555549 */
S2  =  8.33333333332248946124e-03, /* 0x3F811111, 0x1110F8A6 */
S3  = -1.98412698298579493134e-04, /* 0xBF2A01A0, 0x19C161D5 */
S4  =  2.75573137070700676789e-06, /* 0x3EC71DE3, 0x57B1FE7D */
S5  = -2.50507602534068634195e-08, /* 0xBE5AE5E6, 0x8A2B9CEB */
S6  =  1.58969099521155010221e-10; /* 0x3DE5D93A, 0x5ACFD57C */

double
__kernel_sin(double x, double y, int iy)
{
        double z,r,v,w;

        z       =  x*x;
        w       =  z*z;
        r       =  S2+z*(S3+z*S4) + z*w*(S5+z*S6);
        v       =  z*x;
        if(iy==0) return x+v*(S1+z*r);
        else      return x-((z*(half*y-v*r)-y)-v*S1);
}

int main() {
        printf("%.20f\n", __kernel_sin(0.41892385060478199, 4.0204527408880763E-18, 1));
        return 0;
}
