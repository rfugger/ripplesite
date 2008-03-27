import urllib, sys

units = (
    'AUD',
    'GBP',
    'CAD',
    'EUR',
    'XAU',
    'INR',
    'JPY',
    'NZD',
    'XAG',
    'CHF',
)

baseUnit = 'USD'

def main(filename='rates.sql'):
    print "Getting rates URL from finance.yahoo.com."
    unitStr = ""
    for unit in units:
        unitStr = unitStr + unit + baseUnit + '=X+'
    unitStr = unitStr[:-1]
    sock = urllib.urlopen("http://finance.yahoo.com/d/quotes.csv?f=l1&s=%s" % unitStr)
    html = sock.read()
    sock.close()

    # parse into lists
    lines = html.splitlines()
    output = ''
    for unit, line in zip(units, lines):
        output = output + ("update ripple_currencyunits set value=%s where short_name='%s';\n" % (line, unit))
    print "Writing to " + filename
    f = open(filename, 'w')
    f.write(output)
    f.close()
    return output

if __name__ == "__main__":
    retries = 10
    while retries > 0:
        try:
            if len(sys.argv) > 1:
                main(sys.argv[1])
            else:
                main('rates.sql')
            sys.exit(0)
        except TypeError:
            retries -= 1
            