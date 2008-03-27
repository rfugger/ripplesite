from django import template

register = template.Library()

def myStrFormat(value, arg):
  try:
    output = ('%' + arg) % value
  except (ValueError, TypeError):
    return ''
  # trim off leading negative sign of '-0.00'
  if float(output) == 0.0 and output[0] == '-':
    output = output[1:]
  return output

def trimZeroes(value):
  "Display as many decimals as necessary."
  decimals = 8
  try:
    while decimals >= 2:
      output = ('%%.%df' % decimals) % value
      if output[len(output) - 1] != '0':
        break
      decimals -= 1
  except TypeError:
    return value
  return output
  
register.filter('myStrFormat', myStrFormat)
register.filter('trimZeroes', trimZeroes)
