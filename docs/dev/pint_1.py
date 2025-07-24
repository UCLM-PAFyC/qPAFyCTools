# https://pint.readthedocs.io/en/stable/user/defining-quantities.html
# https://pint.readthedocs.io/en/stable/advanced/defining.html
# https://towardsdatascience.com/leveraging-python-pint-units-handler-package-part-1-716a13e96b59/

# osgeo4w console: pip install pint

from pint import UnitRegistry

ureg = UnitRegistry()

accel = 1.34567 * ureg.parse_units('meter/second**2')
# The standard string formatting code
print('The str is {!s}'.format(accel))
# The str is 1.3 meter / second ** 2
print('The str is {:.2f~P}'.format(accel))
print('The str is {:.2~P}'.format(accel))
print('The str is {:~P.2f}'.format(accel))
print('The str is {:~P.2}'.format(accel))
print('The str is {:~P}'.format(accel.units))

# The standard representation formatting code
print('The repr is {!r}'.format(accel))
# The repr is <Quantity(1.3, 'meter / second ** 2')>

# Accessing useful attributes
print('The magnitude is {0.magnitude} with units {0.units}'.format(accel))
# The magnitude is 1.3 with units meter / second ** 2

ureg.formatter.default_format = '.3f'
Q_ = ureg.Quantity
home = Q_(25.4, ureg.degC)
print(home.to('degF'))
# 77.720 degree_Fahrenheit
print(home.to('kelvin'))
# 298.550 kelvin
print(home.to('degR'))
# 537.390 degree_Rankine
print(home)
print(home.magnitude)
print(type(home.magnitude))
print(home.units)
print(home.dimensionality)
print('degree' in ureg)
print(ureg.get_compatible_units('[mass]'))
print(ureg.get_compatible_units('[temperature]'))
angle_deg = ureg('180.0 deg')
print(angle_deg.magnitude)
angle_rad = angle_deg.to('rad')
print(angle_rad.magnitude)

quantity = ureg.Quantity
try:
    temp = quantity(30.5, 'celsius')
    try:
        temp_k = temp.to('kelvin')
    except Exception as error:
        # handle the exception
        print("An exception occurred:", error)
except Exception as error:
    # handle the exception
    print("An exception occurred:", error)
temp_compatible_units = ureg.get_compatible_units(temp.dimensionality)
for unit in temp_compatible_units:
    yo_str = str(unit)
    yo_name = ureg.get_name((str(unit)))
    yo = ureg.get_symbol(str(unit))
    tu = 1
yo = 1



