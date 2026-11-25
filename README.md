# Tire fitment explorer

Interactive Streamlit display for the Fleet Tire Optimization Strategy capstone project at the University of Waterloo. It shows how tire width, rim diameter, tire type, tread depth and pressure change stopping distance, slip and other health and safety indicators in summer and winter conditions.

It is a screening model calibrated to published tire tests, not measured data for any specific tire. See the "Model and sources" tab in the Technical view and [SOURCES.md](SOURCES.md).

## Please read before using

- **Not safety advice.** The model shows the direction and rough size of each effect so that choices can be compared. Individual tires differ more between brands than between sizes. Do not use it to choose tires for a specific vehicle or to predict a real stopping distance.
- **A student project.** The content is the authors' own work and has not been reviewed or endorsed by any organisation.
- **Placeholder fleet data.** The vehicle classes are generic and are not a real fleet. Cost, wear and fuel figures are simple scaling rules, not purchase or service records.
- **No data collected.** The app has no accounts, stores nothing you enter, and has Streamlit usage statistics turned off.

## Files

- `app.py`: the Streamlit page.
- `tire_model.py`: the model (lookup tables and functions, no Streamlit).
- `tests/test_model.py`: checks that the model still matches its published calibration anchors.
- `tests/test_app.py`: smoke test that the page renders in both views, for every vehicle, and in demo mode.
- `SOURCES.md`: the published tests and references behind the model, with links, and the parts that have no published support.
- `LICENSE`, `NOTICE`, `CITATION.cff`: licence, copyright and attribution, and how to cite.

## What is on the page

- Braking animation: the selected setup against the factory tire (factory size, new tread, recommended pressure). Click it to pause. The Simple view calls this the "factory tire"; the Technical view calls it the "reference".
- Tire picture: the size code as printed on a sidewall (for example 225/65R17), what each number means, and the tire drawn to scale from the front, from the side and as a footprint, with the factory size as a dashed outline.
- Simple view for a poster audience and Technical view with the charts and the model notes.
- Demo mode: cycles through preset scenarios with a large heading showing the conditions, on a dark background. Run it full screen with the sidebar collapsed: the first screen fits a 13-inch laptop and the comparison charts are one scroll below.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Test

```
pip install -r requirements-dev.txt
python -m pytest -q
```

## Deploy on Streamlit Community Cloud

Sign in at share.streamlit.io with this GitHub account, choose this repository, branch `main`, and main file `app.py`.

## Sources

[SOURCES.md](SOURCES.md) lists the published tire tests the model was tuned against, the papers and standard references for hydroplaning, wheel slip, manual lifting and CO2, and the parts of the model that are judgement values with no published support. Only sources whose figures could be confirmed are cited, in the file and in the app. The figures were read from search results on 2026-11-18, because the pages could not be opened directly from the build environment.

## Authors

Harrison Cormier, Ashley Pacek and Varvara Blinova. The three authors contributed equally.

## Acknowledgements

The work was conducted at the University of Waterloo as part of the Fleet Tire Optimization Strategy capstone project.

Parts of the code and documentation were written with AI coding assistance (Claude Code) and reviewed by the authors.

## How to cite

> Cormier, H., Pacek, A., and Blinova, V. (2026). *Tire fitment explorer* [Software]. University of Waterloo. https://github.com/harrison-cormier/tire-explorer

GitHub's "Cite this repository" button reads the same details from `CITATION.cff`.

## Licence

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova, held equally.

Code and documentation are released under the [Apache License 2.0](LICENSE). Copyright and third-party notices are in [NOTICE](NOTICE). You may use, change and share the work, including commercially, as long as you keep the licence and notices and say what you changed.

The app is built on [Streamlit](https://streamlit.io) (Apache-2.0), [Plotly](https://plotly.com/python/) (MIT) and [NumPy](https://numpy.org) (BSD-3-Clause).

Tire makers, test organisations and publications are named only to credit the published tests the model was tuned against. Their names belong to their owners, and none of them reviewed, sponsored or endorsed this project.

## Contributing

Issues and pull requests are welcome. Please keep `python -m pytest -q` passing. If a change moves a calibration anchor, cite the test or paper that justifies it in the test docstring, in the "Model and sources" tab and in `SOURCES.md`, and only cite sources whose figures you have confirmed.
