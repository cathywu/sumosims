from numpy import meshgrid, array, linspace, diff, sum
from numpy import transpose as T
import matplotlib.pyplot as plt
import matplotlib.colors as colors


cdict = {
        'red'  :  ((0., 0., 0.), (0.2, 1., 1.), (0.6, 1., 1.), (1., 0., 0.)),
        'green':  ((0., 0., 0.), (0.2, 0., 0.), (0.6, 1., 1.), (1., 1., 1.)),
        'blue' :  ((0., 0., 0.), (0.2, 0., 0.), (0.6, 0., 0.), (1., 0., 0.))
        }
my_cmap = colors.LinearSegmentedColormap('my_colormap', cdict, 1024)

def scatter(title, (x, xlabel), 
                   (y, ylabel), 
                   (s, smin, smax, slabel)):

    fig, ax = plt.subplots()

    cax = ax.scatter(x, y, c=s, 
            vmin=smin, vmax=smax, 
            s=3, edgecolors='none', 
            cmap=my_cmap)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.margins(0)
    ax.invert_yaxis()

    # Add colorbar
    ticks = [smin, (smin+smax)/2, smax]
    cbar = fig.colorbar(cax, ticks=ticks)
    cbar.ax.set_yticklabels(ticks)  # vertically oriented colorbar
    cbar.ax.set_ylabel(slabel, rotation=270, labelpad=20)

    return plt

def pcolor(title, (xrng, xlabel), 
                  (yrng, ylabel), 
                  (s, smin, smax, slabel)):

    fig, ax = plt.subplots()

    #y, x = mgrid[yrng, xrng]
    #cax = ax.pcolor(x, y, s, 
    x, y = meshgrid(xrng, yrng)
    cax = ax.pcolormesh(x, y, array(s),
            vmin=smin, vmax=smax, 
            cmap=my_cmap)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.axis('tight')
    ax.invert_yaxis()

    # Add colorbar
    ticks = [smin, (smin+smax)/2, smax]
    cbar = fig.colorbar(cax, ticks=ticks)
    cbar.ax.set_yticklabels(ticks)  # vertically oriented colorbar
    cbar.ax.set_ylabel(slabel, rotation=270, labelpad=20)

    return plt

def pcolor_multi(title, (xrng, xlabel), 
                  (yrng, ylabel), 
                  (vdict, vlabel), 
                  (sdict, smin, smax, slabel),
                  (odict, olabel, otypes),
                  (fdict, fmin, fmax, (flabel, funit1, funit2))):

    numlanes = len(sdict)

    fig, axarr = plt.subplots(numlanes+1, 2, 
            sharex=True, 
            figsize=(16, 9), dpi=100)

    vax = axarr[-1,0]
    fax1 = axarr[-1,1]
    fax2 = fax1.twinx()

    x, y = meshgrid(xrng, yrng)

    for (ax, ax2, sid) in zip(axarr[:,0], axarr[:,1], sorted(sdict)):
        tv = T(array(sdict[sid]))
        cax = ax.pcolormesh(T(y), T(x), tv,
                vmin=smin, vmax=smax, 
                cmap=my_cmap)
        ax.set_ylabel(xlabel)
        ax.axis('tight')

        tv = T(array(odict[sid]))
        cx2 = ax2.pcolormesh(T(y), T(x), tv)
        ax2.axis('tight')

        vax.plot(yrng, vdict[sid], label="lane %s" % sid)
        handles, labels = vax.get_legend_handles_labels()
        lbl = handles[-1]
        ax.set_title("lane %s" % sid, color=lbl.get_c())

        fax1.plot(yrng, fdict[sid], label="lane %s" % sid)
        fax2.plot(yrng, array(fdict[sid])/array(vdict[sid]), '--', label="lane %s" % sid)

    vax.set_ylabel(vlabel)
    vax.set_ylim([smin, smax])
    vax.set_xlabel(ylabel)

    fax1.set_ylabel(flabel + " " + funit1)
    fax2.set_ylabel(flabel + " " + funit2)
    if fmin is not None and fmax is not None:
        fax1.set_ylim([fmin, fmax])
        fax2.set_ylim([fmin/4, fmax/4])
    fax1.set_xlabel(ylabel)
    fig.text(0.5, 0.975, title, 
            horizontalalignment='center', verticalalignment='top')
    # Add colorbar
    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.84, 0.35, 0.02, 0.55])
    cbar_ax2 = fig.add_axes([0.84, 0.1, 0.02, 0.2])

    ticks = linspace(smin, smax, 6)
    cbar = fig.colorbar(cax, cax=cbar_ax, ticks=ticks)
    cbar.ax.set_yticklabels(ticks)  # vertically oriented colorbar
    cbar.ax.set_ylabel(slabel, rotation=270, labelpad=20)

    cb = fig.colorbar(cx2, cax=cbar_ax2, ticks=otypes.values())
    cb.ax.set_yticklabels(otypes.keys())

    return plt
