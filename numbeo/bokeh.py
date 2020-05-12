import re
import pandas as pd

from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Select, HoverTool
from bokeh.models.widgets import Button
from bokeh.layouts import column, row

# Read in the data
URLS = ['https://www.numbeo.com/quality-of-life/rankings.jsp',
        'https://www.numbeo.com/cost-of-living/rankings.jsp',
        'https://www.numbeo.com/property-investment/rankings.jsp',
        'https://www.numbeo.com/crime/rankings.jsp',
        'https://www.numbeo.com/health-care/rankings.jsp',
        'https://www.numbeo.com/pollution/rankings.jsp',
        'https://www.numbeo.com/traffic/rankings.jsp']


def numbeo_data_retrieval():
    # Loads stored CSV data to DataFrame
    city_quality = pd.DataFrame()
    for URL in URLS:
        temp_df = pd.read_csv(
            '../data/'+re.findall('\/(.*?)\/', URL)[1]+'.csv')
        temp_df.drop(columns=['Unnamed: 0'], inplace=True)
        if city_quality.empty:
            city_quality = city_quality.append(temp_df)
        city_quality = city_quality.merge(
            temp_df, left_on='City', right_on='City',
            how='inner', suffixes=('', '_delete'))
    city_quality.drop(list(city_quality.filter(
        regex='_delete$')), axis=1, inplace=True)
    return city_quality


city_quality = numbeo_data_retrieval()[:-1]
df = city_quality.iloc[:, 1:]
df = ((df-df.min())/(df.max()-df.min()))
df['City'] = city_quality['City']

df['city'] = [x.split(',')[0].strip() for x in df['City']]
df['country'] = [x.split(',')[-1].strip() for x in df['City']]
df['state'] = [x.split(',')[1].strip() if len(
    x.split(',')) > 2 else None for x in df['City']]
df.pop('Safety Index')
df.pop('Price To Income Ratio')
df.pop('Time Index(in minutes)')
df.pop('Local Purchasing Power Index')

# Create the ColumnDataSource object

world = df[df['country'] != 'United States']
usa = df[df['country'] == 'United States']
WORLD_DICT = {x: world[x] for x in world.columns}
USA_DICT = {x: usa[x] for x in usa.columns}


def initialize():
    temp = {x: world[x] for x in world.columns}
    temp.update({'x': world.iloc[:, 0]})
    temp.update({'y': world.iloc[:, 1]})

    temp2 = {x: usa[x] for x in usa.columns}
    temp2.update({'x': usa.iloc[:, 0]})
    temp2.update({'y': usa.iloc[:, 1]})

    return temp, temp2


WORLD = ColumnDataSource(initialize()[0])
USA = ColumnDataSource(initialize()[1])

all_hover = HoverTool(names=['global_circle'],
                      tooltips=[('City', '@{city}'),
                                ('Country', '@{country}'),
                                ])

us_hover = HoverTool(names=['us_circle'],
                     tooltips=[('City', '@{city}'),
                               ('State', '@{state}'),
                               ('Country', '@{country}'),
                               ])


# Creating the scatter plot
plot1 = figure(x_axis_label=df.columns[0],
               y_axis_label=df.columns[1],
               title=f'{df.columns[0]} VS {df.columns[1]}',
               tools=[all_hover, us_hover, 'box_select'],
               background_fill_color='goldenrod',
               background_fill_alpha=0.1)

c1 = plot1.circle(x='x',
                  y='y',
                  source=WORLD,
                  size=7,
                  # {'field': 'country', 'transform': color_map},
                  color='blue',
                  selection_color='red',
                  legend_label='World',
                  alpha=0.5,
                  name='global_circle')

c2 = plot1.circle(x='x',
                  y='y',
                  source=USA,
                  size=7,
                  color='green',
                  legend_label='United States',
                  alpha=0.5,
                  name='us_circle')

plot1.title.align = 'center'
plot1.title.text_font = 'helvetica'
plot1.title.text_color = 'goldenrod'
plot1.title.text_font_style = 'bold'

plot1.legend.location = 'top_center'
plot1.legend.click_policy = 'hide'

plot1.xaxis.axis_label_text_font_style = 'bold'
plot1.yaxis.axis_label_text_font_style = 'bold'


# Creating the select widget

select_y = Select(options=df.columns.tolist()[:-4],
                  value=df.columns.tolist()[1],
                  title='Select a new Y-axis attribute')

select_x = Select(options=df.columns.tolist()[:-4],
                  value=df.columns.tolist()[0],
                  title='Select a new X-axis attribute')

label_button = Button(label="Move Legend")

# Define the callback function


def set_axis(axis, ind):
    temp = WORLD_DICT
    temp2 = USA_DICT
    if axis == 'y':
        temp.update({'x': WORLD.data['x']})
        temp.update({'y': world.iloc[:, ind]})
        temp2.update({'x': USA.data['x']})
        temp2.update({'y': usa.iloc[:, ind]})
    if axis == 'x':
        temp.update({'x': world.iloc[:, ind]})
        temp.update({'y': WORLD.data['y']})
        temp2.update({'x': usa.iloc[:, ind]})
        temp2.update({'y': USA.data['y']})
    return temp, temp2


def y_callback(attr, old, new):
    for ind, x in enumerate(df.columns):
        if new == x:
            WORLD.data, USA.data = set_axis('y', ind)
            plot1.title.text = f'{plot1.xaxis.axis_label} VS {df.columns[ind]}'
            plot1.yaxis.axis_label = df.columns[ind]


def x_callback(attr, old, new):
    for ind, x in enumerate(df.columns):
        if new == x:
            WORLD.data, USA.data = set_axis('x', ind)
            plot1.title.text = f'{df.columns[ind]} VS {plot1.yaxis.axis_label}'
            plot1.xaxis.axis_label = df.columns[ind]


def button_callback(event):
    if plot1.legend.location == 'top_center':
        plot1.legend.location = 'top_left'
    elif plot1.legend.location == 'top_left':
        plot1.legend.location = 'top_right'
    elif plot1.legend.location == 'top_right':
        plot1.legend.location = 'top_center'


select_y.on_change('value', y_callback)
select_x.on_change('value', x_callback)
label_button.on_click(button_callback)

# Add the layout to the application

layout = column(row(select_y, select_x), plot1, label_button)

curdoc().add_root(layout)
