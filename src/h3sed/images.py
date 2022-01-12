"""
Contains embedded image and icon resources. Auto-generated.

------------------------------------------------------------------------------
This file is part of h3sed - Heroes3 Savegame Editor.
Released under the MIT License.

@created     21.03.2020
@modified    12.01.2022
------------------------------------------------------------------------------
"""
try:
    import wx
    from wx.lib.embeddedimage import PyEmbeddedImage
except ImportError:
    class PyEmbeddedImage(object):
        """Data stand-in for wx.lib.embeddedimage.PyEmbeddedImage."""
        def __init__(self, data):
            self.data = data


"""Returns the application icon bundle, for several sizes and colour depths."""
def get_appicons():
    icons = wx.IconBundle()
    [icons.AddIcon(i.Icon) for i in [
        Icon_16x16_32bit, Icon_16x16_16bit,
        Icon_24x24_32bit, Icon_24x24_16bit,
        Icon_32x32_32bit, Icon_32x32_16bit
    ]]
    return icons


"""Heroes3 Savegame Editor application 16x16 icon, 32-bit colour."""
Icon_16x16_32bit = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAALHRFWHRDcmVhdGlvbiBUaW1l"
    "AEwgMjEgbeRydHMgMjAyMCAxNTo0NDo0NyArMDIwMMsTHzoAAAAHdElNRQfkAxUNODRflfVU"
    "AAAACXBIWXMAAAsSAAALEgHS3X78AAAABGdBTUEAALGPC/xhBQAAAtxJREFUeNp1U2tIk2EU"
    "fr5vn9vUecn7baQkS8s0MlNL8dMkZPnDbJSIUBb+iJAIuuAPtxUEhRKFPyT8UxIhIUKii7Tc"
    "N9HhpRAvlWWbl2mpqVOXc6nbW5tm0+zAezgv5/Y857wvsFUUv0+a3ZDL5Zv2dt//RNHy9CR5"
    "UJJIkmIota4tnrx5VUs2khStz7JJhTyTbC9CO1862zshzUpC5B6GndAP4kjcAmQymdLh03Yg"
    "NTnUbrI7to/0h7rm/kGSIaFIc7U7UVW5El37YQeK3PRQ0liZbO+u3p7HsytpRrT6Yk4gmyUr"
    "hjc9Cl+fWUyNrcBbNIP4tNuI9NVjfLAHFqFk5Iv+2xPnAoxd+XsZ2Q9dUwgNeoQfi/MYGliF"
    "xQLoxwjExkoYDMCYbhaM2e0f+I4ZWK2rWBW6IkAcjmBxACZGbDAt2UDWXLC6MA1GtBeSQ/tw"
    "PicIIR5baTgKzC0buaIrx9HbrcfQx6/o7wN8PBiYFy3gudIIDGAQFBaO09e1ytiIzZX+paBq"
    "tqXTJg2RJi1ht9gH48HAvNGKxcWNIDeCntfduHftqPJmuZbaaY2Kq5clyLlwB7tCQzA2x8PA"
    "ZwF4PL7DOTtJYYX2RF6eFLJc6RYKzB/jReMM+nqeo66+lwsTUazY24YQiYvDx3e3op4bBdd6"
    "F/GpNrZ2/TFptkyT3U+Rs9G0fdeK2jIBKZVRhHvsRlZMn0jhMZrcKHAn/kKoi064keoKX1LM"
    "rr9IB4VT2Snq5HAGS8RmXxM3aqQRFcuHZ2AU3nX149ylAmg1Zu67BelVTWblsm4BP9dodrOA"
    "69owOz66xjUMOmBpuntW4BVAwc83BhPvB6BS1aLNQJQbYDmDKQbT5o0hyjJoRXycD4YnNwNQ"
    "89KqFAkIgqJL0dFUhpa3Zs6Js8ZE8RHhx6wjCLbZOHrBiMSEMM5pJLce1iVw+YUlXHnDEpvC"
    "sqzzLxzSmzjBgTNsfqZQ8Qs1XyOB+yzbpwAAAABJRU5ErkJggg=="
)


"""Heroes3 Savegame Editor application 16x16 icon, 16-bit colour."""
Icon_16x16_16bit = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAALHRFWHRDcmVhdGlvbiBUaW1l"
    "AEwgMjEgbeRydHMgMjAyMCAxNTo0NDo0NyArMDIwMMsTHzoAAAAHdElNRQfkAxUNOQKJNFGM"
    "AAAACXBIWXMAAAsSAAALEgHS3X78AAAABGdBTUEAALGPC/xhBQAAAaRQTFRF////j2gcc0kc"
    "UU08VFRUcGZASkIpeHNcjXctAAAAwJ8H+vPbdEwLNCYAb2Q2cUYGWkgbXSwBWEkDtJgI4spe"
    "rJKAdloKfGMwUUw8eUsFjXoJpYIHzrcyx72swKRePB0BmXAEZjwCQCsBVykCrIsHfVQBwKAK"
    "+vPZYTsCdlwLFQgAZUYKopMTblggj3IyPSQAWTABfEoDqowI7Nxev6+BQzAJUTIMhG8KvaM0"
    "5tKIvZ8vUzAFXzoJkGYIuaSEkXAo4cyEVFJKTDgOlnADrIQVcUICi2ACjWMCzLyDl24aiXQ6"
    "SkUC0LxNnHsxjWcaVikCm3EFpH8DyLKEw6VPSC4AXE4Ta00Ky7BTspA0g1cCiWQBro0L6dNc"
    "sZyAq4kvrYs6Gg0AX1EYcEUBtZMzmXMenncElm8Dr5EG7uJyrZBZhVcFTTsimnsr6diapYEu"
    "w6MJpYED0a8Hyq1Zo3oYSUUyJBUAqI4wQiYBu6ILtpsJ3cU0vbmsUkEbtZc5h2kU2sFvXE8F"
    "wqIL8+idi2wU0LdfvqRLkHk3OCwB3cQzwqZMk35Efn5+nz2PAgAAAAF0Uk5TAEDm2GYAAADS"
    "SURBVHjaY2AAg24g5mSAAs7WtvaOagbOzi6YSF19Q2MTC0NzC5RfWlZeUVlVXVML1cOWk5uX"
    "X1DIXVRcAhFITEpOSU1Lz8jMyoYIhIaFR0RGRcfExsUngAW8fXz9/AMCjYOCGUIgSpycXVzd"
    "3I09PL2gtlhYWlnb2Brb2Ts4Qtylq6dvYGhkbGJqZg5RoaTMoKKqpq6hqaWtA+JLSDIwSEnL"
    "yMrJMzAoKAIFBAQZGISERUTFgGxxkAoOkDlc3Dy8QJqPH0gwMgEJZhYGVpA32BkA2WYnWed2"
    "jJAAAAAASUVORK5CYII="
)


"""Heroes3 Savegame Editor application 24x24 icon, 32-bit colour."""
Icon_24x24_32bit = PyEmbeddedImage(
    "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"
)


"""Heroes3 Savegame Editor application 24x24 icon, 16-bit colour."""
Icon_24x24_16bit = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAMAAADXqc3KAAAALHRFWHRDcmVhdGlvbiBUaW1l"
    "AEwgMjEgbeRydHMgMjAyMCAxNTo0NDo0NyArMDIwMMsTHzoAAAAHdElNRQfkAxUNOCBFTyEp"
    "AAAACXBIWXMAAAsSAAALEgHS3X78AAAABGdBTUEAALGPC/xhBQAAAtlQTFRF////g1sWbEAI"
    "bD4VXCgCIiAZPjw2MCwgNTAbMy0cPTs0MisTupxJd2Ujd2Qa7N6dnZyVSSMBiG4qf282AAAA"
    "rp5nt59wrIk0cV0WhWgLPBUAvJ0H5Mtd/PntXDUIalUOoJBBcEQGln89YiwBgmkEtZoJxKMG"
    "7diI18rAiF4PRDQHUCoBRzkjMhgAkXpEd04GincHtZYL6NaKzsS/gF4jv6JZQysBs5RKjmAC"
    "ODQogVMDUiUBVEoFr5cKnXkEpoME2MMn6+HEqY5zt5tETSQBu5wGIhgAaT0DXTMCY1IEflIC"
    "qIQGw6UM+OzGppGAimsTGhEBNSIDpYQcsqIQEQkATiICVEQCYzQCnHUE7+F8vbmsSjgDPCIB"
    "EwMAonwRno0MLCkAjHIat59hsZc+YkEAQx4AdEUDhVwB5tYy+vLZoYpEWz0Ie2EdYj4KdVoG"
    "vqYr59eX5tKMxKlCe1wSPhoCo4AJlHREb0sQwqRL4Mh7mJWGX0gAnHccqopBuJchqYEPZz4E"
    "bkkFimAJm3UJpIhImngh4s6FvaJjKyIKvJ4XkmkCrokabEIBkWUCqoc9STsYMzAB3stonX4P"
    "jGgdp34KpH8Cn35EwJ0+TjsRWzsAOiwAmYkRm4I4rZAs0bhfckMCq4oF4cosoH5HzrRWqZph"
    "TCsC1rtklXIFeEwCvJwN5M8xk3Y/il4TjHcggmMOon0Zs5cH59g49u7Rn304dkQFc0USHhIJ"
    "n4tFyK5RwqZZwZ8G8eWI7eC2iV8dzLFdODQktJZQxKZE6dWRr40yyqUEvJUI278F7N6y0Ldm"
    "l20IbVgfIB0UGA4Aqo80uqELX19fkHk9U0YVRjgLdVwlZVkjppAL1LYM8N6Kv7+/LhsBlXEZ"
    "cloVZ1kpWUwdeXFV4shI+vPUOjo6pIksnn0c3cqEdGtKpIcwoX8qWUwizcrB1b1wp5NVQTgS"
    "YlUeYVk5iH08MTExal4wLikbeN0ivQAAAAF0Uk5TAEDm2GYAAAGxSURBVHjaY2DAB968fccg"
    "8j7qA5B55eMnJImnz56/8LwW+ZKBQeTVrddIEnfXzbtnsPL+g4cMIo8ePxFBSFxKvHzl6rlr"
    "12+I3Lx1+w5C/EzxWe3l51RdFzqev1BxESHOeeDgocPNR+yPHvM9fuLkqdMwcZHtHjsKdy73"
    "tvPetXvP3rh9++E61oavW7/errfXbsPGTZu3bN0G15G4dO6yiuUr0u1WrspcvWbx5BCYzOw5"
    "c+dVzPdI71qwMHPR4iUMujD3Tpg4abJ/j/UUu6kZmdOmz2CYOQumpaOzq9uqx6u3KyPTuamv"
    "H+He6prauvqGxqbmjMyW1rZ2uLhIfkFhUXFJqHtpRmZZeUVlFcJZSckpqalp6aoZmVnZObl5"
    "CTCZEJdQhjCv8Ai1yCiT6JjYuHiYjJu7B4OnvZe3j6+flX8AQ2BQMETc0sqagcHG1s7ewdHJ"
    "2QUoYOaqDbZCTx9EGqgaGhmbmII8Z2ZuAdahpAwiVVTV1DU0tUBMbR1dECUhKQXWKC0jKycP"
    "MVxBEUTy8EJ4fPwCgkLCYDWiYuJAipGJmQXEZWVjYGDngEQdFzcDAJiOlEQRp6PjAAAAAElF"
    "TkSuQmCC"
)


"""Heroes3 Savegame Editor application 32x32 icon, 32-bit colour."""
Icon_32x32_32bit = PyEmbeddedImage(
    "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"
)


"""Heroes3 Savegame Editor application 32x32 icon, 16-bit colour."""
Icon_32x32_16bit = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAALHRFWHRDcmVhdGlvbiBUaW1l"
    "AEwgMjEgbeRydHMgMjAyMCAxNTo0NDo0NyArMDIwMMsTHzoAAAAHdElNRQfkAxUNNyG10A1w"
    "AAAACXBIWXMAAAsSAAALEgHS3X78AAAABGdBTUEAALGPC/xhBQAAAPNQTFRF////bkIDTh0C"
    "Zi8DAAAA3MJspIEAPRcBAAEA9ue0////9uWmzbZa48p9/fvr49GHtYsSq4YFxq0Qj2EDnHUA"
    "7tuXe1MRuJ8K160A9+q6uJwmzrhCEgMCTykBhFgCrYkPKg8AlGsE4tEItpMhAwEBAgEBxao8"
    "ilIEkXAGe1gABgAAHgIAFQAAhWgJmX8ho4Uu9O3JoIQiyaxK/vngvqMstpIV7OGzAAAD1rtf"
    "xaE2pIILyrRPnXYKxaY82L1mUzgAvKZL3sd2JAcA+fLUn3sA2LNW2s+Zupsrr5Q61LRerZQs"
    "pYw4xJ84kXYjbE0BvJ0xz7NSwH+08QAAAAF0Uk5TAEDm2GYAAAIKSURBVHjajZNte5MwFIZJ"
    "ckhKO0whtGk7gQb6FqfVVTuZXbs536dO//+vMaGg0E/yIRcn576e85yTxHH+7wMAu3ahEbXy"
    "iwWfOxB6JQE7G7UBT4vfEIyykoBekvC2BuweN2OQ29G4BHZ6f3UCPOq9D1KGpYSJfhUnwMP3"
    "KchQhlYC0I+fs5M8uvwaCyklLSXcbw8neT/fDL6QcERTa7PgSkE7f59+8LgKA/rR2vSF+PR5"
    "1hoCoYfigKVa0UBm3QKnUatLmJBbpVRKl0JRmY27ihDcUpjcr/d+oSjSUWpdajJxETSB25u7"
    "jZsoopWQI6+LU/5exP80IOPrPT8QHIuEBkah7xsLrHFgwDOstUa4T2+oAdB1YpJRs8h1luSC"
    "IBQJZYB3guxOJ5mgvJ8goZBVWK2KAWrlKXX5m+2WTXPUN8Bw6F4N3jYB+arHz/ILhmMirYf4"
    "cuO/bloIfH6uGWNoqe0cXqD1S6SbQGfKYgcijJblcer5s4vnedYkEMGmkGDlnGC5WjFATQIU"
    "Q+bK0oSm5t4SlcPMmaNFVrcCCY4dpxNKFdlBkgmJ7a7IWH2lU3JsRqbS604H41IbiBAVIOIa"
    "CEwFHCVHIBjXgEuqbqX1SCaVOQxPqzlGdS1pLhyr8w6cH00G3t+dsoKojxEGw5JALnUriU75"
    "bHpn1RP2n/B+SWBMag2ol2Nkfv8A3KAxCtlEjPsAAAAASUVORK5CYII="
)


"""Icon for the Hero page in a savefile tab."""
PageHero = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAEoElEQVRYw+2Wf0yUdRzHX9/n"
    "AS9OOQVKCRINkRSl/BUyDdc0nYkup5FKy8RmrbA2Y8MllZqDVdrSOZouNy1n5fy1kEQq2RLj"
    "ODUz5or0Qn7IAeePe7iD447He7794c6tiXC69Ze8//luz/b9vN+fX+/vA/3ox4MOca8XFCEk"
    "wLJ5ChvXvondfpmGpjo0zc3az5vF/yYgSJw1U7KruIgGey1XtACDTT7aPT6utjRRa6+n3tnJ"
    "vh8CIccNC5X8vRWRbPpwI53+LtqcDq5oARouVdHYeB2AhJHxpKVPIw246Tsu958ILbmwUMkX"
    "Zc1Hj5nNwEGjsB6ayrlzNQCYw0ELgLfGjaa52V9+FXNAkJslZfGBvkWIUAT4XSWoEakA2Ery"
    "2LrjEEkJFrQONxGqiiliIGU2H+aAzhvLU/He1BkxPJFde45x8KQU910BRQiZNVPiqrcSMy4d"
    "YXRy+sx5khIsONs8DB1moczmo+1aF5/mT2bZu5XIgIYwOrGV5PHEqEhexCP7EtGrgAuly6Wu"
    "HZW6zynrrPly35Z0uXP947IwN16mDEbu25IufR0t0jB06Ty/Ti6ZhUQgF0xVpCKELMixyF45"
    "+hLxT7MT1WXHVbuVb7/aDsCIESl8tqOF0uP5ZOdV4bZvR1HDeTuviOGPqDTZPmDD+qW4r1WT"
    "kZHBb8ey5X1X4Pudc6X1wGLpqS2SuVnIvYVPymhVkYbeLnXtqIxWFVmQY5E/f5MpDX+9NPR2"
    "WXvidWk7sEQaers0DF0aRpcszI2X9zyEihDytedhxvRULA/H0eHRKCmrZldxEdmvvo+7W5C9"
    "MJlV66qpsxawYlUxAF41nEhT4HacgNfg1EUJ8k7OPgVkpgmaPWGseXkMisnM72fPUFGjkrdy"
    "Ek+NSQZg2xd7sV2QRMWoxEYHyH5pLq2tDQDU1vzFtsMCQ8oe+dTeBEjYaHewYfRjEDtUJXZo"
    "FNGDhxBl7uDr0iZOV5/nYMkfnKkLY/JYg4gwWDg/ncWrfyJKvciPZeXkvZOP8FqputDzJoTk"
    "hM9MGIj9bwduzcP8ebNRTGZmTA+npLwSULjsgtYbKnOmxWJ+SKHiu4V4brgYPTaZ+IxPgnnK"
    "niqghCLAEhnFypxFONs8FG05QpWtmqLiKiJUFXe3QHfrxEbf6rnXZwDQ2NhGY30zqxcIICDu"
    "1u6QKuD2uJjw7HMkVZ5lytMKgyKH4WuvpukqTEoEywCFwydVoBkA6y82GpwClyZvDd9dsg/J"
    "CTPTBCnjUjB1+GhtbsDtsRATF8/MOekADIocwhSPhslk40jlAAK6gzGjHiV1komKU5cpmGah"
    "cLdb3JMVB5/ezDTB0qw0XsjZRkX5R3R0CRyam4/3/EpwqTPTBCtfSWdiahx+fwvW2jD8/lZ8"
    "XYKkBAuFu90oQkhD9jyEorfdT5k4nuTE8bQ5HWzdXMzosYms2VwHQDBg8LVMGZeC4fdSWlHD"
    "pZYBTB6p82WZBKkGZ4CQBWx6Kw6Hs5nuTkHr9Vs+YA7oeNVwzv3Zfce94KMVNwQcGng7FI7a"
    "jJC8Rtzlq0SqIAK3DQHxn7NH4UawMfL+f/n60Y8HD/8CJkMWqBywNrcAAAAASUVORK5CYII="
)


"""Toolbar icon for refresh button."""
ToolbarRefresh = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAABnUlEQVQ4y9XUPWtUQRTG8d/c"
    "rGuljeJLIwmYtTeKinZ2YuHdBUmnYCUWhuRjKDZaxiaVKO4mEPIBFFGxymKxIQiCaJqAik0I"
    "ZsciN5u7d2/WlHq6M+fMf+Y88zD86xGGVp+pqJrAOEbwWdV7122AlpOia+qeDgfOq+qawZTg"
    "WKH6SzSLWUELidT43sCXjgqWBOf3OeUnqdM7SdJXWnJAYrEHi9q4hZpoDHW8HUav9GUbZgQX"
    "MticTXdM+p2Tois6MQyY5JpHBFMZbHkAtr2+gLECI5bfsOuc4Him7KMB2HbcxJEC7mc5MKjl"
    "mt6UzpNaxSpoOpTpS0uU6hQ1/CC6mwHX9uHgU3icZZMUgamOlqrosOCsZm/j+s7phVEv90wX"
    "rZS/MguC0cLGd7jUt/bCQcF0Vv9qzXK5D2PB6FFHUB+AVczhTLbywL3dl678RakfuKKpLahk"
    "Y07nYK8lnuxt7H5vBcFFPO/dO/R1vBLd0LBVbuzdxo+imuhh0WNZfMF9m65q+D78+2q6LVrU"
    "sJ77dSYwii3Bim/aec3+v/gDVpZ0g1sFQpUAAAAASUVORK5CYII="
)
