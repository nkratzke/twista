import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import PIL
import numpy as np
import math

from wordcloud import WordCloud


def color_intensity(size, max_size, word, marked):
    if word in marked:
        return PIL.ImageColor.getrgb('rgb(255, 0, 0)')
    col = 255 - int(math.sqrt(size / max_size) * 255)
    return PIL.ImageColor.getrgb('rgb(%i, %i, %i)' % (col, col, col))


def plot_init(figsize=(16, 9), title='', axis=None, xaxis='', yaxis='', xlim=None, ylim=None):
    if axis:
        ax = axis
    else:
        fig = plt.figure(figsize=figsize)
        ax = fig.gca()

    ax.set_title(title)
    ax.set_ylabel(yaxis)
    ax.set_xlabel(xaxis)
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)

    return ax


def word_cloud(frequencies, ax=None, title='', mark=[]):
    axis = plot_init(title=title, axis=ax)

    wordcloud = WordCloud(
        max_words=len(frequencies.keys()),
        width=1024,
        height=768,
        background_color='white',
        min_font_size=5,
        max_font_size=100,
        color_func=lambda word, font_size, position, orientation, font_path, random_state: color_intensity(font_size, 100, word, mark)
    ).generate_from_frequencies(frequencies)

    axis.imshow(wordcloud, interpolation='bilinear')
    axis.set_axis_off()
    # plt.axis('off')

    return axis


def scatter_plot(
        data,
        ax=None,
        colors=None,
        xaxis="X Values",
        yaxis="Y Values",
        title='',
        xlim=None,
        ylim=None,
        alpha=0.5,
        legend=True,
        invert_xaxis=False,
        invert_yaxis=False
):
    axis = plot_init(title=title, axis=ax, xaxis=xaxis, yaxis=yaxis, xlim=xlim, ylim=ylim)

    for category, tuples in data.items():
        xs = [x for x, y in tuples]
        ys = [y for x, y in tuples]

        if colors:
            axis.scatter(xs, ys, color=colors[category], label=category, alpha=alpha)
        else:
            axis.scatter(xs, ys, label=category, alpha=alpha)

    if legend:
        axis.legend(frameon=False)

    if invert_xaxis:
        axis.invert_xaxis()

    if invert_yaxis:
        axis.invert_yaxis()

    return axis


def punchcard_plot(data, on_row, on_col, rows, cols, title=''):
    fig = plot_init(title=title, figsize=(cols / 2, rows / 2), xaxis='Hour', yaxis='Weekday')

    # Inspired by 
    # https://stackoverflow.com/questions/14849815
    table = np.zeros((rows, cols))
    max_value = table[0][0]

    grouped_rows = data.group(by=on_row)
    for row in sorted(grouped_rows.keys()):
        grouped_cols = grouped_rows[row].frequencies(on=on_col)
        for col in sorted(grouped_cols.keys()):
            table[row][col] = grouped_cols[col]
            if max_value < grouped_cols[col]:
                max_value = grouped_cols[col]

    table = table / float(max_value)

    plt.axes(frameon=False)
    plt.gca().yaxis.grid(linestyle='--')
    plt.gca().xaxis.grid(linestyle='--')

    plt.axis('equal')
    plt.xlim(-0.5, cols - 1 + 0.5)
    plt.ylim(-0.5, rows - 1 + 0.5)
    plt.yticks(np.arange(rows), ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
    plt.xticks(np.arange(cols))

    xs = []
    ys = []
    sizes = []
    colors = []
    for row in range(0, rows):
        for col in range(0, cols):
            xs.append(col)
            ys.append(row)
            sizes.append(table[row][col] * 1000)
            colors.append((0, 0, 0, max([0.33, table[row][col]])))

    plt.scatter(xs, ys, s=sizes, c=colors)
    plt.gca().invert_yaxis()
    return fig


def pie_plot(frequencies, ax=None, colors=None, title=''):
    axis = plot_init(title=title, axis=ax)
    axis.set_aspect('equal')
    labels = list(frequencies.keys())
    fracs = list(frequencies.values())

    if colors:
        cs = [colors[l] for l in labels]
        axis.pie(fracs, labels=labels, colors=cs, pctdistance=0.45, autopct='%1.0f%%', counterclock=False)
    else:
        axis.pie(fracs, labels=labels, pctdistance=0.45, autopct='%1.0f%%', counterclock=False)

    circle = plt.Circle((0, 0), radius=0.55, color='white', fill=True)
    axis.add_artist(circle)
    #plt.setp(outside, width=0.5, edgecolor='white')

    return axis


def _normalize(timelines):
    total = {}
    for tag, data in timelines.items():
        for key, value in data.items():
            if key not in total:
                total[key] = 0
            total[key] += value

    norm = {}
    for tag, data in timelines.items():
        norm[tag] = {}
        for key, value in data.items():
            norm[tag][key] = value / total[key]

    return norm


def timeline_plot(timelines, ax=None, colors=None, title='', xaxis='', yaxis='', ylim=None, norm=False):
    axis = plot_init(title=title, axis=ax, xaxis=xaxis, yaxis=yaxis, ylim=ylim)

    process = _normalize(timelines) if norm else timelines

    for timeline, data in process.items():
        xs = sorted(data.keys())
        ys = [data[d] for d in xs]
        if colors:
            c = colors[timeline] if timeline in colors else '#bbbbbb'
            axis.plot_date(xs, ys, xdate=True, label=timeline, color=c, ls='-', lw=2, alpha=0.5)
        else:
            axis.plot_date(xs, ys, xdate=True, label=timeline, ls='-', lw=2, alpha=0.5)

    axis.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    axis.xaxis.set_major_locator(mdates.WeekdayLocator())

    if norm:
        if not ylim:
            axis.set_ylim(0, 1)
        axis.set_yticklabels([f"{p}%" for p in range(0, 110, 20)])

    plt.gcf().autofmt_xdate()

    axis.legend(loc='upper right', frameon=False)
    return axis


def line_plot(lines, ax=None, colors=None, title='', xaxis='', yaxis='', ylim=None, norm=False, x_invert=False):
    axis = plot_init(title=title, axis=ax, xaxis=xaxis, yaxis=yaxis, ylim=ylim)

    process = _normalize(lines) if norm else lines


    for line, data in process.items():
        xs = sorted(data.keys())
        ys = [data[d] for d in xs]
        if colors:
            c = colors[line] if line in colors else '#bbbbbb'
            axis.plot(xs, ys, label=line, color=c, ls='-', lw=2, alpha=0.5)
        else:
            axis.plot(xs, ys, label=line, ls='-', lw=2, alpha=0.5)

    if x_invert:
        axis.invert_xaxis()

    if norm:
        if not ylim:
            axis.set_ylim(0, 1)
        axis.set_yticklabels([f"{p}%" for p in range(0, 110, 20)])

    axis.legend(loc='upper right', frameon=False)
    return axis


def bar_plot(histograms, labels, xaxis="X Values", yaxis="Y Values", title='', width=3/4):
    fig = plot_init(title=title, xaxis=xaxis, yaxis=yaxis)

    stack = [0] * len(histograms[0].keys())

    i = 0
    for h in histograms:
        xs = list(h.keys())
        xs.sort()
        ys = [h[x] for x in xs]
        plt.bar(xs, ys, bottom=stack, align='center', alpha=0.75, label=labels[i])
        i += 1
        stack = [sum(x) for x in zip(ys, stack)]

    plt.legend()
    return fig


def bar_chart(frequencies, colors=None, xaxis='', yaxis='', title=''):
    fig = plot_init(title=title, xaxis=xaxis, yaxis=yaxis)

    labels = []
    xs = []
    ys = []
    i = 0
    for label, value in frequencies.items():
        xs.append(i)
        ys.append(value)
        labels.append(label)
        i += 1

    if colors:
        plt.bar(xs, ys, color=[colors[label] for label in labels])
    else:
        plt.bar(xs, ys)

    plt.gca().set_xticks(np.arange(len(labels)))
    plt.gca().set_xticklabels(labels)
    return fig


def box_plot(frequencies, ax=None, xaxis='', yaxis='', title='', xlim=None, ylim=None, horizontal=False):
    axis = plot_init(title=title, axis=ax, xaxis=xaxis, yaxis=yaxis, xlim=xlim, ylim=ylim)

    data = []
    labels = []
    for group, values in frequencies.items():
        labels.append(group)
        data.append(values)

    axis.boxplot(data, labels=labels, vert=not horizontal)
    return axis