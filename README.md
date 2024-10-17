# Aurora borealis visibility, or ABV

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [Running it](#running-it)
   * [Setup](#setup)
   * [Plot the aurora events, this is it!](#plot-the-aurora-events-this-is-it)
   * [Tips](#tips)
- [Cached data](#cached-data)
- [Sources and credits](#sources-and-credits)

<!-- TOC end -->

ABV will graph aurora borealis visibility throughout years, with the planetary [_K_<sub>p</sub>-index](https://en.wikipedia.org/wiki/K-index) plotted and with decent thresholds.

This was created to show to my wife the best time of the year and annual average occurrences of auroras in the northern hemisphere, because she didn't believe me when I told her about the _K_<sub>p</sub>-index and multi year cycles of correlated sunspots etc. She wanted to see an aurora but nobody could tell her the best time nor place to go with minimal guarantee to see one.

**There you have it:** pay attention to the roughly 7-years or 11-years long solar cycles suggested through sunsports counts, plus streak of geomagnetic storms confirmed by _K_<sub>p</sub>-index above certain thresholds.

I'm a complete ignorant and armchair nerd about this, so take it all with a sol-sized grain of salt.

<!-- TOC --><a name="running-it"></a>
## Running it

<!-- TOC --><a name="setup"></a>
### Setup

Prep step... install Python's virtualenv on your system, which on macOS can be done with `brew install pyenv pyenv-virtualenv` and you'll need to adapt that for your system like Linux.

Local shell config in `~/.profile`:

```
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Python stuff:

```
git clone https://github.com/caiobegotti/aurora-borealis-visibility.git
cd aurora-borealis-visibility/

pyenv install 3.8.10
pyenv virtualenv 3.8.10 myenv
pyenv activate myenv

pyenv local myenv
pip install --upgrade pip
pip install matplotlib
```

<!-- TOC --><a name="plot-the-aurora-events-this-is-it"></a>
### Plot the aurora events, this is it!

```
./ABV.py 2024
```

<!-- TOC --><a name="tips"></a>
### Tips

1. Download all available years at once, updates local cache:
	```
	for y in $(seq 1932 2024); do ./ABV.py ${y}; done
	```

1. Combine multiple years locally so you can visualize them together, say, using the data between 2010 and today. You will need the montage command from ImageMagick, likely via `brew install imagemagick` on macOS:

	```
	montage kp_index_201* kp_index_202* -tile 5x5 -geometry +2+2 combined_image.png
	```
	
	Just note that `5x5` makes a pretty big image already hard to view in small monitors.

<!-- TOC --><a name="cached-data"></a>
## Cached data

The `cache` directory holds all available data since 1932 until the end of Q3 2024. If you're not online it will simply process the data from the cache, otherwise it pulls the data via the API client but that may break over time if the service changes format etc.

<!-- TOC --><a name="sources-and-credits"></a>
## Sources and credits

The file `getKpindex.py` and respective data come from the [GFZ German Research Centre for Geosciences](https://kp.gfz-potsdam.de/en/data) (under CC BY 4.0).

<!-- TOC Sunspots data is under CC BY-NC 4.0 license and comes from [WDC-SILSO, Royal Observatory of Belgium, Brussels](https://www.sidc.be/SILSO/datafiles). -->