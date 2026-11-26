# Sources

This file lists the published tests and references the model rests on, what the model takes from each, and the parts of the model that have no published support. The "Model and sources" tab of the app carries the same list.

The model is a screening tool. It was tuned by hand so that its outputs land near the published results below. It was not fitted to raw data, and nothing here is a measurement of a specific tire made by this project.

## How the list was checked

Each source below was searched for on 2026-11-18 and is included only because the search returned the figure or finding quoted here, from the source itself or from named coverage of it. The pages could not be opened directly from the build environment, so the figures were read from search results. Sources named in earlier project notes that could not be supported this way have been removed (see the last section).

## Published tire tests

| What the model takes from it | Source |
|---|---|
| Cool dry road: winter tires stop about 15% longer than summer tires. In the test, braking from 62 mph (100 km/h) at 5.5 °C, summer tires needed 5.8 m less on average than winter tires. | What Car?, "Should I buy winter tyres?" https://www.whatcar.com/news/winter-tyres/ |
| Cold wet road: winter tires stop shorter than summer tires. Braking from 50 mph at 4 °C, premium winter tires stopped 4.0 m sooner on average than premium summer tires. | What Car?, same article |
| Packed snow: summer tires take at least twice the distance of winter tires. The winter tires stopped the test car in an average of 17.7 m and the summer tires took more than twice that. | What Car?, "Snow and ice" https://www.whatcar.com/news/snow-and-ice/n11592 |
| Wet road by temperature: all-season tires lead summer tires in the cold and the two meet between 10 and 15 °C. At +2 °C on a wet road all-season tires stopped almost 6.5 m shorter than summer tires from 80 km/h; at +12 °C the two were comparable. | Tyre Reviews, "2025 Summer and All Season Combined Tyre Test" https://www.tyrereviews.com/Article/2025-Summer-and-All-Season-Combined-Tyre-Test.htm |
| Ice: winter tires stop well short of all-season tires. From 12 mph on an ice rink, studless winter tires stopped in 35.1 ft against 53.6 ft for all-season tires, about a third shorter. | Tire Rack, ice rink braking tests https://www.tirerack.com/tires/tests/testDisplay.jsp?ttid=116 |
| Width in winter: narrower tires have the advantage in aquaplaning, slush and on snow, wider tires on a dry road, and the differences between widths are smaller than between tire models. One winter tire model was tested in five sizes from 195/65 R15 to 225/40 R18. In 7 mm of standing water the 225 mm tires lost contact at about 70 km/h and the 195 mm tires held on to above 80 km/h. | ADAC, "Reifenbreiten im Winter: lieber schmal oder extrabreit?" https://presse.adac.de/meldungen/adac-ev/tests/reifenbreitenvergleich-winterreifen.html |
| Width on packed snow barely matters: four widths of one winter tire on one car gave results close enough that a driver would not notice the difference. | Tyre Reviews wide against narrow winter tire test, as reported by Motor1, "Wide Versus Narrow Winter Tires: It Doesn't Really Matter Which You Choose" https://www.motor1.com/news/696279/wide-vs-narrow-winter-tires-explained/ |
| Width in summer: wider tires stop shorter on dry and wet roads, and narrower tires aquaplane at a higher speed. In the tests ADAC evaluated, 195 mm tires stopped in 38.8 m on average and 225 mm tires in 36.7 m on a dry road. | ADAC, "Schmale vs. breite Reifen: Die Wahrheit über die perfekte Reifengröße" https://www.adac.de/rund-ums-fahrzeug/ausstattung-technik-zubehoer/reifen/sicherheit/reifengroesse/ |
| Tread wear in the wet: braking barely changes down to 4 mm, then is about 17% longer at 2 mm (31.9 m new, 31.4 m at 4 mm, 37.3 m at 2 mm; winter tires in 185/65 R15). | ADAC, "Test abgefahrene Reifen: So schnell wird es gefährlich" https://www.adac.de/rund-ums-fahrzeug/ausstattung-technik-zubehoer/reifen/sicherheit/abgefahrene-reifen/ and the Automobile Club du Luxembourg report of the same joint test https://autotouring.acl.lu/?p=9905 |
| Tread wear on snow: about 2% per mm down to 4 mm, steeper below. Snow traction fell 8.8% on average at 4 mm and 15.9% at 2 mm, and ADAC advises replacing winter tires at 4 mm. | ADAC, same worn-tire test |

Where the model is more cautious than a source, that is deliberate. ADAC's dry-road figures for 195 mm against 225 mm tires and its aquaplaning speeds both show a larger effect of width than the model gives, partly because those comparisons also change rim size and tire construction. The model takes the direction from them and keeps the size modest.

## Papers and standard references

| What the model takes from it | Source |
|---|---|
| Hydroplaning onset speed rises with the square root of tire pressure (about 6.35 times the square root of pressure in kPa, in km/h). | Horne, W. B., and Dreher, R. C. (1963). *Phenomena of Pneumatic Tire Hydroplaning*. NASA Technical Note D-2056. https://ntrs.nasa.gov/citations/19640000612 |
| Form of the grip against wheel-slip curve, with a separate parameter set for dry, wet, snow and ice surfaces. | Burckhardt, M. (1993). *Fahrwerktechnik: Radschlupf-Regelsysteme*. Vogel Verlag, Würzburg. |
| 23 kg reference load for manual lifting, used to flag wheel and tire weight at changeover. | Waters, T. R., Putz-Anderson, V., Garg, A., and Fine, L. J. (1993). Revised NIOSH equation for the design and evaluation of manual lifting tasks. *Ergonomics*, 36(7), 749-776. https://doi.org/10.1080/00140139308967940 |
| About 2.3 kg of CO2 per litre of gasoline burned. | Natural Resources Canada, *2026 Fuel Consumption Guide*. https://natural-resources.canada.ca/sites/admin/files/documents/2026-02/2026-Fuel-Consumption-Guide.pdf |
| Pressure change with temperature. | Ideal gas law at constant volume (textbook physics). |

## Parts of the model with no published support

These are judgement values. They set the direction of an effect and a plausible size, and should be replaced with data where the project has it.

- Vehicle classes, masses, placard pressures and fuel baselines in `VEHICLES` are generic placeholders, not a real fleet.
- The friction tables as a whole. Their overall level and the ratios between tire types are set by the tests above; the shape between test points is interpolation.
- Ice friction rising as the ice gets colder. This is the usual expectation for tires on ice, but no source for it was confirmed.
- Slush friction values, and the size of the hydroplaning effect on braking distance in standing water and slush.
- The exponents for width, sidewall height and diameter (only their direction is tied to the width tests above).
- The exact Burckhardt parameter values used are the set commonly quoted for this model; the ice curve is given a mild fall-off after its peak. The values were not checked against the book.
- The 7 °C changeover line on the temperature chart is common industry guidance, shown for reference.
- Price, wear, fuel use, wheel weight, ride harshness, pothole damage and steering response indices are simple scaling rules. The fuel estimate assumes rolling resistance accounts for a quarter of fuel burned.
- The status bands in the "Health and safety" tab are screening thresholds for discussion, not compliance limits.

## Software

| Package | Use | Licence |
|---|---|---|
| Streamlit | Web page and controls | Apache-2.0 |
| Plotly | Charts | MIT |
| NumPy | Numerical work in the model | BSD-3-Clause |

## Names and trademarks

Tire makers, test organisations and publications are named only to credit the published tests the model was tuned against. Their names and product names belong to their owners. None of them reviewed, sponsored or endorsed this project, and no test data, text or images from them are reproduced here beyond the short summary figures cited above.

## Sources removed because they could not be supported

Earlier versions of the model notes named these. They are no longer cited anywhere in the app.

- A Michelin demonstration for the "twice the distance on snow" result. No public page was found; the What Car? test supports the same result.
- A Tyre Reviews test at Test World of tire types at 0 to 15 °C. The article exists, but its results could not be read, so the wet-road result is cited to the 2025 Tyre Reviews test.
- A figure of 0.04 m between 225 and 255 mm tires in snow braking. It was found only on a third-party summary site.
- A Tyre Reviews article with Continental on winter tire wear. The article exists, but its figures could not be read; the ADAC worn-tire test supports the same effect.
- A claim that winter tires stop in half the distance of summer tires on ice. Only the comparison with all-season tires was found.

---

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova. Licensed under the Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
