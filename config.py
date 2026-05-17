import configparser
from os.path import expanduser
import os

config_file_path = expanduser("~/.config/pvfclock.conf")
def read_config(defaults):
    if not os.path.exists(config_file_path):
        # If the file does not exist, write default values
        write_config(defaults)

    config = configparser.ConfigParser()
    config.read(config_file_path)

    # Read the values from the file, falling back to defaults if missing
    x = config['Window'].getint('x') if config.has_option('Window', 'x') else defaults['x']
    y = config['Window'].getint('y') if config.has_option('Window', 'y') else defaults['y']
    w = config['Window'].getint('w') if config.has_option('Window', 'w') else defaults['w']
    h = config['Window'].getint('h') if config.has_option('Window', 'h') else defaults['h']
    lcd_back = config['Colors'].get('lcd_back') if config.has_option('Colors', 'lcd_back') else defaults['lcd_back']
    lcd_face = config['Colors'].get('lcd_face') if config.has_option('Colors', 'lcd_face') else defaults['lcd_face']
    clock_back = config['Colors'].get('clock_back') if config.has_option('Colors', 'clock_back') else defaults['clock_back']
    icon = config['Other'].get('icon') if config.has_option('Other', 'icon') else defaults['icon']
    defaults= {
        'x': x,
        'y': y,
        'w': w,
        'h': h,
        'lcd_back': lcd_back,
        'lcd_face': lcd_face,
        'clock_back': clock_back,
        'icon' : icon
    }
    write_config(defaults)
    return defaults

# The write_config function remains the same as previously defined

def write_config(params):
    config = configparser.ConfigParser()
    # Add the Window section
    config['Window'] = {
        'x': str(params['x']),
        'y': str(params['y']),
        'w': str(params['w']),
        'h': str(params['h'])
    }

    # Add the Colors section
    config['Colors'] = {
        'lcd_back': params['lcd_back'],
        'lcd_face': params['lcd_face'],
        'clock_back': params['clock_back']
    }

    config['Other'] = {
        'icon' : params['icon']
    }


    # Write the configuration to the file
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)


if __name__ == "__main__":
    params= {
        'x': 100,
        'y': 200,
        'w': 300,
        'h': 140,
        'lcd_back': '#006400',
        'lcd_face': '#7fff00',
        'clock_back': '#2f4f4f',
        'icon' : '/usr/share/icons/hicolor/scalable/apps/org.gnome.clocks.svg'
    }
    params = read_config(params)
    print(params)
    
