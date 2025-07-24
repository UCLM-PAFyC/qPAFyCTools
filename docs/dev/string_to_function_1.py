
# osgeo4w console: pip install sympy
# https://github.com/sympy/sympy/blob/master/sympy/physics/units/definitions/unit_definitions.py
# https://github.com/sympy/sympy/blob/master/sympy/physics/units/definitions/dimension_definitions.py
# https://github.com/sympy/sympy/blob/master/sympy/physics/units/systems/si.py

# from sympy import sympify, symbols
# from sympy.physics.units import *
import sympy as sym
from sympy.physics import units as su
# from math import *

expression = "x**2 + 3 * x - 1"
x = sym.symbols('x')
my_function = sym.sympify(expression)
result = my_function.subs(x, 2)
print(result)  # Output: 9

print(sym.sin(float(sym.pi/3)))
#sym.sin(30*sym.degree)
print(float(sym.rad(sym.deg(sym.pi))))

print(su.degree.scale_factor)
print(float(su.degree.scale_factor))
print(su.radian.scale_factor)
print(type(su.radian.scale_factor))

print(su.find_unit(u.kelvin))


