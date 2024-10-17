# Aurora borealis visibility, or ABV

This will graph aurora borealis visibility throughout years, with Kp index plotted.

This was created to show to my wife the best time of the year and annual average occurrences of auroras in the northern hemisphere, because she didn't believe me when I told her about the Kp index and multi year cycles etc.

## Running it

### Setup

Prep step on macOS:

```
brew install pyenv pyenv-virtualenv
```

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
cd aurora-borealis-visibility/

pyenv install 3.8.10
pyenv virtualenv 3.8.10 myenv
pyenv activate myenv

pyenv local myenv
pip install --upgrade pip
pip install matplotlib
```

### Plot the aurora events

```
./ABV.py 2024
```

### Tips

Combine multiple years locally so you can visualize them together, say, using the graphs from several years:

```
montage kp_*.png -tile 7x7 -geometry +2+2 combined_image.png # from imagemagick
```

## Cached data

The `cache` directory holds all available data since 1932 until the end of Q3 2024. If you're not online it will simply process the data from the cache, otherwise it pulls the data via the API client but that may break over time if the service changes format etc.

## API client

The file `getKpindex.py` comes from the [GFZ German Research Centre for Geosciences](https://kp.gfz-potsdam.de/en/data) (which is under CC BY 4.0).
 