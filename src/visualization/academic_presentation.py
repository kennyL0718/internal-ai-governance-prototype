"""Verbatim academic drawing definitions; globals are bound by the portable figure adapter."""

def annual_rate_figure(summary):
    import matplotlib.pyplot as plt
    import numpy as np

    years = [int(r['fiscal_year']) for r in summary]
    rates = [100*float(r['positive_rate']) for r in summary]
    fig, ax = plt.subplots(figsize=(6.5,3.2))
    fig.subplots_adjust(left=.11,right=.985,bottom=.17,top=.96)
    line, = ax.plot(years,rates,color='#21618C',marker='o',lw=1.6,markersize=4)
    require(np.allclose(line.get_ydata(),rates,rtol=0,atol=1e-12), 'Annual line/data mismatch')
    for year, rate in zip(years,rates):
        ax.annotate(f'{rate:.2f}%',(year,rate),xytext=(0,6),textcoords='offset points',ha='center',fontsize=8.5)
    ax.set_ylim(0,max(rates+[1])*1.3)
    ax.set_xticks(years)
    ax.set_xlabel('Fiscal Year',fontsize=9)
    ax.set_ylabel('Implemented Internal AI Governance v2 (%)',fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.grid(axis='y',color='#DCE2E5',linewidth=.6)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    return fig, dict(years=years,rates_pct=rates,annual_controls=summary,visualization_type='line chart')

def export(fig, slug, audit, percent_labels=()):
    import matplotlib.pyplot as plt
    from PIL import Image

    require(not fig.texts and getattr(fig,'_suptitle',None) is None, 'Figure-level text remains')
    require(all(not ax.get_title() for ax in fig.axes), 'Internal axes heading remains')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    texts = []
    for ax in fig.axes:
        texts += list(ax.texts)+[ax.xaxis.label,ax.yaxis.label]
        lo,hi = sorted(ax.get_xlim())
        texts += [t for v,t in zip(ax.get_xticks(),ax.get_xticklabels()) if lo <= v <= hi]
        lo,hi = sorted(ax.get_ylim())
        texts += [t for v,t in zip(ax.get_yticks(),ax.get_yticklabels()) if lo <= v <= hi]
        if ax.get_legend():
            texts += ax.get_legend().get_texts()
    for legend in fig.legends:
        texts += legend.get_texts()
        box = legend.get_window_extent(renderer)
        require(canvas.contains(box.x0,box.y0) and canvas.contains(box.x1,box.y1), 'Legend is clipped')
    if percent_labels:
        sizes = [(ax.get_window_extent(renderer).width,ax.get_window_extent(renderer).height)
                 for ax in fig.axes]
        require(all(abs(w-sizes[0][0]) < 1e-6 and abs(h-sizes[0][1]) < 1e-6 for w,h in sizes),
                'Annual pies have unequal sizes')
        audit['equal_pie_sizes_verified'] = True
    forbidden = ('Figure ', 'denominator:', 'QA:', 'validation pending', 'Fixed size', 'Fixed index', 'Source:')
    for t in texts:
        if not t.get_visible() or not t.get_text():
            continue
        box = t.get_window_extent(renderer)
        require(box.x0 >= -1 and box.y0 >= -1 and box.x1 <= canvas.x1+1 and box.y1 <= canvas.y1+1,
                'Clipped label: '+t.get_text())
        require(not any(p in t.get_text() for p in forbidden), 'Embedded explanatory text remains')
    boxes = [t.get_window_extent(renderer) for t in percent_labels]
    for i,b in enumerate(boxes):
        for other in boxes[i+1:]:
            require(not b.overlaps(other), 'Overlapping pie percentages')
    target = FIGURES / slug
    target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target.with_suffix('.png'),dpi=300,facecolor='white')
    fig.savefig(target.with_suffix('.pdf'),facecolor='white',metadata={
        'Creator':'Matplotlib / academic proposal figures','CreationDate':None,'ModDate':None})
    preview = PREVIEW / (slug.replace('/','__')+'.png')
    preview.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(preview,dpi=100,facecolor='white')
    pdf = target.with_suffix('.pdf').read_bytes()
    require(b'/Subtype /Image' not in pdf, 'PDF contains a raster image')
    require(b'/FontFile2' in pdf, 'PDF fonts are not embedded')
    with Image.open(target.with_suffix('.png')) as img:
        pixels = list(img.size)
        dpi = list(img.info['dpi'])
        require(min(dpi) >= 299.9, 'PNG resolution below 300 dpi')
        img.verify()
    audit.update(no_internal_title_or_number=True,no_embedded_methodological_notes=True,
        text_canvas_check=True,legend_canvas_check=True,percent_labels_overlap=False,
        png_dpi=dpi,png_pixels=pixels,width_inches=fig.get_figwidth(),height_inches=fig.get_figheight(),
        pdf_vector=True,pdf_fonts_embedded=True,preview=str(preview.relative_to(WORK).as_posix()),
        original_image=str(SOURCE_ASSETS[slug].relative_to(ROOT).as_posix()))
    plt.close(fig)
    return audit

def academic_pies(d, color_map):
    """Presentation-only FY2023–FY2025 view of the unchanged verified assignments."""
    import textwrap
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch

    annual = [a for a in d['annual'] if a['fiscal_year'] in (2023, 2024, 2025)]
    check([a['fiscal_year'] for a in annual] == [2023, 2024, 2025], 'Missing display year')
    check(set(color_map) == set(d['themes']), 'Color mapping does not cover P01–P12')
    order = d['order']
    counts = np.array([[a['counts'][t] for t in order] for a in annual], dtype=int)
    totals = counts.sum(axis=1)
    check(np.all(totals > 0), 'Empty annual assignment set; do not impute a pie')
    check(all(int(n) == a['assignments'] for n, a in zip(totals, annual)), 'Assignment totals differ')
    shares = counts / totals[:, None]
    check(np.allclose(shares.sum(axis=1), 1, rtol=0, atol=1e-12), 'Pie shares do not sum to 100%')
    fig = plt.figure(figsize=(6.5, 4.2))
    percent_labels = []
    all_colors = [color_map[t]['color'] for t in order]
    for i, (a, values) in enumerate(zip(annual, counts)):
        ax = fig.add_axes([.018 + i * .327, .49, .31, .46])
        wedges, _, labels = ax.pie(values, colors=all_colors, startangle=90, counterclock=False,
            autopct=lambda p: f'{p:.1f}%' if p >= 6.7 else '', pctdistance=.69,
            wedgeprops=dict(linewidth=0, edgecolor='white'), textprops=dict(fontsize=8.3))
        for t, w, label, value in zip(order, wedges, labels, values):
            w.set_hatch(color_map[t]['hatch'] or None)
            check(np.allclose(w.get_facecolor()[:3], to_rgb(color_map[t]['color'])), 'Slice color changed')
            check(abs(abs(w.theta2 - w.theta1) / 360 - value / a['assignments']) < 3e-7,
                  'Drawn slice differs from assignment share')
            lum = sum(c * k for c, k in zip(to_rgb(color_map[t]['color']), (.2126, .7152, .0722)))
            label.set_color('white' if lum < .56 else '#16232B')
            if label.get_text():
                percent_labels.append(label)
        ax.set_xlim(-1.03, 1.03)
        ax.set_ylim(-1.03, 1.03)
        ax.text(0, 1.10, f"FY{a['fiscal_year']} | n = {a['assignments']}",
                ha='center', va='bottom', fontsize=9, color='#16232B')
        ax.set_aspect('equal')
        ax.set_axis_off()
    legend = fig.legend(
        [Patch(facecolor=color_map[t]['color'], edgecolor='white', linewidth=0,
               hatch=color_map[t]['hatch'] or None) for t in order],
        [textwrap.fill(t + '  ' + d['themes'][t], width=43, break_long_words=False,
                       break_on_hyphens=False) for t in order],
        loc='lower center', bbox_to_anchor=(.5, .015), ncol=2, frameon=False,
        fontsize=7.8, handlelength=1.3, handleheight=1.1, columnspacing=1.9,
        labelspacing=.5, handletextpad=.6, borderpad=0)
    check(len(legend.get_texts()) == 12, 'Shared legend is incomplete')
    check([' '.join(t.get_text().split()) for t in legend.get_texts()] ==
          [' '.join((t+' '+d['themes'][t]).split()) for t in order], 'Legend category wording changed')
    rounded_totals = np.round(shares * 100, 1).sum(axis=1)
    check(np.all(np.abs(rounded_totals-100) <= .6), 'Rounded composition exceeds rounding tolerance')
    audit = dict(years=[a['fiscal_year'] for a in annual],
        annual_assignments=[int(n) for n in totals], category_order=order,
        counts=counts.tolist(), shares=shares.tolist(),
        categories=d['themes'], color_map={t: color_map[t]['color'] for t in order},
        percentages_sum_to_100=True, original_colors_preserved=True,
        legend_categories=order, percent_label_threshold=6.7,
        rounded_percentage_sums=rounded_totals.tolist(),
        nonempty_percent_labels=len(percent_labels))
    return fig, audit, percent_labels

def academic_annual_heatmap(annual, pooled):
    """Same annual cells, color scale and sparsity marks, sized for a proposal page."""
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import FuncFormatter

    upper = max(5, math.ceil(max(r['positive_rate_pct'] or 0 for r in annual + pooled) / 5) * 5)
    cmap = LinearSegmentedColormap.from_list('governance_teal_academic',
                                            ('#F2F6F6', '#72BBB2', '#007D78', '#174D55'))
    cmap.set_bad('#E4E7EB')
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 5.1))
    fig.subplots_adjust(left=.205, right=.875, top=.92, bottom=.09, wspace=.055)
    matrices = []
    for ax, year in zip(axes, YEARS):
        lookup = {(r['gics_sector'], r['firm_size_group']): r for r in annual if r['fiscal_year'] == year}
        matrix = np.array([[lookup[s, z]['positive_rate_pct']
                           if lookup[s, z]['positive_rate_pct'] is not None else np.nan
                           for z in SIZES] for s in SECTORS])
        im = ax.pcolormesh(np.arange(4)-.5, np.arange(12)-.5, np.ma.masked_invalid(matrix),
                          cmap=cmap, norm=Normalize(0, upper), edgecolors='white',
                          linewidth=.65, rasterized=False)
        ax.set_xlim(-.5, 2.5)
        ax.set_ylim(10.5, -.5)
        ax.set_xticks(range(3), SIZES)
        ax.set_yticks(range(11), SECTORS if year == YEARS[0] else [''] * 11)
        ax.tick_params(axis='both', length=0, labelsize=7.5, pad=4)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i, sector in enumerate(SECTORS):
            for j, size in enumerate(SIZES):
                r = lookup[sector, size]
                value = r['positive_rate_pct']
                flags = ('*' if r['small_sample'] else '') + ('†' if r['sparse_positive'] else '')
                label = 'NA\nN=0' if value is None else f'{value:.1f}%{flags}\n{r["positive_n"]}/{r["total_n"]}'
                ax.text(j, i, label, ha='center', va='center', fontsize=8, linespacing=1.3,
                        color='white' if value is not None and value/upper > .55 else '#162E3C')
                if r['small_sample']:
                    ax.add_patch(Rectangle((j-.5, i-.5), 1, 1, fill=False, hatch='//',
                                          edgecolor='#788B91', linewidth=0, alpha=.42))
        n = sum(r['total_n'] for r in lookup.values())
        p = sum(r['positive_n'] for r in lookup.values())
        ax.text(.5, 1.018, f'FY{year}\n{p}/{n:,} ({100*p/n:.2f}%)', transform=ax.transAxes,
                ha='center', va='bottom', fontsize=8, linespacing=1.3)
        matrices.append(matrix.tolist())
    axes[1].set_xlabel('Firm Size', fontsize=8.2, labelpad=7)
    cb = fig.colorbar(im, cax=fig.add_axes([.89, .145, .015, .72]))
    cb.set_label('Governance Positive Rate (%)', fontsize=8, labelpad=5)
    cb.ax.tick_params(labelsize=7)
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.0f}'))
    cb.solids.set_rasterized(False)
    audit = dict(years=list(YEARS), sector_order=list(SECTORS), size_order=list(SIZES),
                 matrices=matrices, scale_limits=[0, upper], small_sample_threshold=SMALL_N,
                 sparse_positive_threshold=SPARSE_P, visualization_type='heatmap')
    return fig, audit

def academic_exclusion_bars(comparison):
    """Presentation of unchanged pooled metrics with essential value annotations."""
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import PercentFormatter

    fig, ax = plt.subplots(figsize=(6.5, 3.55))
    fig.subplots_adjust(left=.105, right=.985, top=.84, bottom=.17)
    x, width = np.arange(len(comparison)), .32
    for field, shift, label, color in [
        ('all_industries', -width/2, 'All industries', '#78929B'),
        ('excluding_financials_it', width/2, 'Excluding Financials and Information Technology', '#007D78'),
    ]:
        values = [r[field]['positive_rate_pct'] for r in comparison]
        bars = ax.bar(x+shift, values, width=width, label=label, color=color, linewidth=0)
        require(np.allclose([b.get_height() for b in bars], values, rtol=0, atol=1e-12), 'Bar/data mismatch')
        for bar, r in zip(bars, comparison):
            m = r[field]
            ax.annotate(f"{m['positive_rate_pct']:.2f}%\n{m['positive_n']}/{m['total_n']:,}",
                        (bar.get_x()+bar.get_width()/2, bar.get_height()), xytext=(0,4),
                        textcoords='offset points', ha='center', va='bottom', fontsize=8.2, linespacing=1.3)
    ax.set_xticks(x, ['S&P 500\nLarge', 'S&P MidCap 400\nMid', 'S&P SmallCap 600\nSmall'])
    ax.tick_params(labelsize=8)
    ax.set_ylim(0, 12)
    ax.set_ylabel('Governance-positive firm-years (%)', fontsize=8.5)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.grid(axis='y', color='#DCE2E5', linewidth=.6)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    fig.legend(*ax.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.5,.985),
               frameon=False, ncol=2, fontsize=8, handlelength=1.6, columnspacing=1.4)
    return fig, dict(comparison=comparison, visualization_type='grouped bar chart',
                     period=list(YEARS), size_order=list(SIZES))
