# Ease Grid Popup

A Blender add-on that puts **interpolation and easing in one popup**, like Mine-imator.

Press **T** in the Graph Editor, Dope Sheet, or Timeline and pick from one grid:

- **Other:** Linear, Constant, Bezier
- **Ease In**, **Ease Out**, **Ease In & Out:** Sine, Quad, Cubic, Quart, Quint, Expo, Circ, Back, Bounce, Elastic

One click sets both the interpolation and the easing on the selected keyframes.

Made for Blender 4.2 and newer (tested on 5.1).

## Install

1. Download `ease_grid_popup.py`: open the file on GitHub, then click the download icon (**Download raw file**).
2. In Blender go to **Edit > Preferences > Add-ons**.
3. Open the small dropdown arrow (top right) and choose **Install from Disk**.
4. Pick `ease_grid_popup.py`, then tick the checkbox to enable it.

Now hover over the Graph Editor or Dope Sheet, select some keyframes, and press **T**.

## Getting a newer version

Updates are not automatic for this download yet. The add-on's built-in update check looks for updates on the author's own computer, so on your machine it won't find anything.

- In **Edit > Preferences > Add-ons > Ease Grid Popup**, untick **Check for updates on startup** so you don't see an error message about it.
- To update, download the newest `ease_grid_popup.py` from this repository and install it again with **Install from Disk** (same steps as above). It replaces the old version. If Blender still shows the old behavior, restart it.

## Notes

- The add-on takes over the **T** key in the Graph Editor and Dope Sheet while it's enabled. Disable it to get the normal menu back.
- Ease In / Out only has a visible effect on the easing types (Sine through Elastic). Linear, Constant and Bezier ignore it.
