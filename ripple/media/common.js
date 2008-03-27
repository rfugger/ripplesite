var convertibleUnits = new Array();
var accountUnits = new Array();
var selectedUnits;
var precision = 2;

function setDisplayUnits(select)
{
  if (select.options)
  {
    if (select.options[select.selectedIndex].value * 1 >= 0)
      selectedUnits = convertibleUnits[select.options[select.selectedIndex].value];
    else
      selectedUnits = null;
    recalculate();
  }
}

function setPrecision(select)
{
  if (select.options)
  {
    precision = select.options[select.selectedIndex].value * 1; // convert string to number
    recalculate();
  }
}

function formatNumber(number, decimals, currencySymbol, useParentheses)
{
  var tmpNum = number;

  // Return the right number of decimal places
  tmpNum *= Math.pow(10, decimals);
  tmpNum = Math.round(tmpNum);
  var i, zeroes = 0;
  for (i = 1; i <= decimals; i++) // see how many trailing zeroes need to get put back on
  {
    if (tmpNum % Math.pow(10, i) == 0)
      zeroes++
  }
  tmpNum /= Math.pow(10, decimals);

  var tmpStr = new String(tmpNum);
  if (zeroes == decimals && zeroes > 0) // put back the decimal place
    tmpStr = tmpStr + '.';
  for (zeroes; zeroes > 0; zeroes--) // add back trailing zeroes
    tmpStr = tmpStr + '0';

  // Insert currency symbol (after negative sign, if present)
  if (currencySymbol != '')
  {
    if (number < 0)
      tmpStr = tmpStr.substring(0,1) + currencySymbol + tmpStr.substring(1, tmpStr.length);
    else
      tmpStr = currencySymbol + tmpStr
  }

  // See if we need to put parenthesis around the number
  if (useParentheses && number < 0)
    tmpStr = "(" + tmpStr.substring(1, tmpStr.length) + ")";

  return tmpStr;
}
