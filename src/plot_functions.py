import pandas as pd

#For plotting
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from cartopy.io import shapereader
import contextily as cx

import seaborn as sns
import pycountry

save_path = '/home/lhasbini/como_school/figure/'
unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]

# Co-occurence matrix
def matrix_co_occurence(df_all, unique_events,
                        save=False, save_path=save_path, save_name="co_occurence_matrix.png") :
    appeal_codes = df_all['appealCode'].unique()
    # Step 1: Create the co-occurrence matrix
    co_occurrence_matrix = pd.DataFrame(0, index=unique_events, columns=unique_events)

    for appeal in appeal_codes :
        report = df_all.loc[df_all.appealCode == appeal]
        event_list = report['Hazard'].tolist()
        if len(event_list) > 1 :
            for i in range(len(event_list)):
                for j in range(i, len(event_list)):
                    if (event_list[i] in unique_events) and (event_list[j] in unique_events) :
                        if i != j:
                            co_occurrence_matrix.loc[event_list[i], event_list[j]] += 1
                            co_occurrence_matrix.loc[event_list[j], event_list[i]] += 1

    # Step 2: Plot the matrix
    fig=plt.figure(figsize=(10, 8))
    sns.heatmap(co_occurrence_matrix, annot=True, cmap="YlGnBu", fmt="d",
                annot_kws={"size": 16})  # Increase annotation font size
    plt.title("Event Co-Occurrence Matrix", fontsize=16)  # Increase title font size
    plt.xticks(fontsize=16, rotation=45, ha='right')  # Increase x-axis tick font size
    plt.yticks(fontsize=16, rotation=45, va='top')  # Increase y-axis tick font size
    #plt.show()
    fig.tight_layout()
    if save :
        fig.savefig(save_path+save_name, transparent=True)
    return(fig)

def map_nb_compounds(nb_compound_country,
                     colormap = 'plasma_r', vmax = 20, cbar_title='Number of Compound Events',
                     save=False, save_path=save_path, save_name="map_nb_compound.png"):
    '''
    nb_country : Dictionnary with the number of events found for each country
        dict keys correspond to the countries
    '''
    # Initialize figure and axis with Cartopy projection
    fig, ax = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})

    # Set up the colormap
    cmap = plt.get_cmap(colormap)  # You can change this colormap if needed
    norm = mcolors.Normalize(vmin=0, vmax=vmax)

    # Add features: land, coastlines, and borders
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')

    # Load the Natural Earth shapefiles
    shapefile = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
    reader = shpreader.Reader(shapefile)
    countries = reader.records()

    # Loop over countries in the shapefile and color them based on the hazard value
    for country in countries:
        iso3 = country.attributes['ADM0_A3']

        # If the country's ISO3 code is in the hazard dict, color it
        if iso3 in nb_compound_country:
            hazard_value = nb_compound_country[iso3]
            color = cmap(norm(hazard_value))
        else :
            color = 'lightgrey'
        ax.add_geometries([country.geometry], ccrs.PlateCarree(), facecolor=color, edgecolor='black')

    # Add a colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])  # Only needed for the colorbar to function properly
    cbar = plt.colorbar(sm, ax=ax, orientation='horizontal', label='Number of compound', pad=0.02)
    cbar.set_label(cbar_title, fontsize=14)
    cbar.ax.tick_params(labelsize=12)

    # Set a title
    #ax.set_title('Number of compound events per country', fontsize=18)

    fig.tight_layout()
    if save :
        fig.savefig(save_path+save_name, transparent=True)
    return(fig)

def map_nb_hazards(nb_compound_country, hazards_list,
                   colormap = 'plasma_r', vmax = 20, cbar_title='Number of Compound Events',
                   save=False, save_path=save_path, save_name="map_nb_compound.png"):
    """
    Plot at maximum 12 hazards maps
    """
    if len(hazards_list) <= 2:
        n_row = 1
        n_col = len(hazards_list)
    elif len(hazards_list) > 2 and len(hazards_list) <= 6:
        n_row = 2
        n_col = (len(hazards_list) + 1) // 2
    elif len(hazards_list) > 6 and len(hazards_list) <= 12:
        n_row = 3
        n_col = (len(hazards_list) + 2) // 3
    else:
        raise ValueError("Too many hazards")

    fig, ax = plt.subplots(1, 1, figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})
    gs = gridspec.GridSpec(n_row, n_col + 1, width_ratios=[1]*n_col + [0.05], wspace=0.1)

    # Create map axes
    ax = [fig.add_subplot(gs[i, j], projection=ccrs.PlateCarree()) for i in range(n_row) for j in range(n_col)]

    # Set up the colormap
    cmap = plt.get_cmap(colormap)
    norm = mcolors.Normalize(vmin=0, vmax=vmax)

    # Add features: land, coastlines, and borders to each map axis
    for axi in ax:
        axi.add_feature(cfeature.LAND)
        axi.add_feature(cfeature.COASTLINE)
        axi.add_feature(cfeature.BORDERS, linestyle=':')

    # Load the Natural Earth shapefiles
    shapefile = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
    reader = shpreader.Reader(shapefile)
    countries = reader.records()

    # Loop over the hazards and plot each one on its respective subplot
    for id_haz, haz in enumerate(hazards_list):
        shapefile = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
        reader = shpreader.Reader(shapefile)
        countries = reader.records()
        for country in countries:
            iso3 = country.attributes['ADM0_A3']

            # If the country's ISO3 code is in the hazard dict, color it
            if iso3 in nb_compound_country[haz] : #.get(haz, {}):
                hazard_value = nb_compound_country[haz][iso3]
                color = cmap(norm(hazard_value))
            else:
                color = 'lightgrey'
            ax[id_haz].add_geometries([country.geometry], ccrs.PlateCarree(), facecolor=color, edgecolor='black')
        ax[id_haz].set_title(haz, fontsize=14)

    # Create a separate axis for the colorbar
    cbar_ax = fig.add_axes([0.15, 0.05, 0.7, 0.02])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    #sm.set_array([])
    cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal', pad=0.2, shrink=0.5)
    cbar.set_label(cbar_title, fontsize=14)
    cbar.ax.tick_params(labelsize=12)

    # Adjust layout
    #fig.tight_layout()
    fig.subplots_adjust(wspace=0.01, hspace=0.05)

    # Save the figure if required
    if save:
        fig.savefig(save_path + save_name, transparent=True)

    return(fig)

def format_plot(ax, crs):
    """formatting for all plots"""
    cx.add_basemap(ax, crs=crs)
    #ax.add_feature(cfeature.LAND)
    #ax.add_feature(cfeature.OCEAN)
    #ax.add_feature(cfeature.COASTLINE,linewidth=0.3)
    ax.add_feature(cfeature.BORDERS, linestyle=':',linewidth=0.3)
    #ax.add_feature(cfeature.LAKES, alpha=0.5)
    #ax.add_feature(cfeature.RIVERS)
    gl = ax.gridlines(draw_labels=True, dms=True)
    gl.xlabels_top = False
    gl.ylabels_left = False
    gl.xlines = False
    gl.ylines = False
    gl.xlabel_style = {'size': 16}
    gl.ylabel_style = {'size':16}
    ax.legend(fontsize=30, loc='upper left')
