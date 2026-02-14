# SARA (Society of Amateur Radio Astronomers) — Research Notes

> Researched 2026-02-14 for the Space Station project

## Membership — $20 USD/year

- Website: https://radio-astronomy.org/
- Bimonthly journal: "Radio Astronomy" (electronic delivery)
- Monthly Zoom observation parties: 1st Sunday, 2pm Eastern
- Conference archives going back to 2006
- 10% store discount on orders $50+
- Student/teacher grants: $200–$500 per project — https://radio-astronomy.org/grants

## Relevant SARA Kits & Projects

### Scope in a Box (~$179 USD)
SARA's flagship RTL-SDR hydrogen line kit.
- WiFi grid dish + LNA + 1420 MHz bandpass filter + RTL-SDR
- Comes with **ezRA** software: https://github.com/tedcline/ezRA
- US-only shipping, but component list is public
- https://radio-astronomy.org/node/366

We are building a more capable version of this with our offset dish + swappable feeds.

### IBT — Itty Bitty Telescope (~$70 USD)
- Small satellite dish + LNB at 12.2–12.7 GHz
- Detects solar radio emission, demonstrates blackbody radiation
- Same frequency band as our Ku-band maser feed — validates the approach
- Original design by Chuck Forster, improved by Kerry Smith
- https://www.gb.nrao.edu/epo/ibt.shtml

### SuperSID ($48 USD)
- VLF solar flare monitor using 1m loop antenna + sound card
- Stanford Solar Center collaboration
- Runs on same RPi simultaneously — cheap complementary instrument
- https://radio-astronomy.org/node/276

### Radio JOVE 2.1 (~$200 USD)
- 20 MHz HF: Jupiter decametric bursts + solar radio emissions
- SDRplay RSP1B + dual-dipole antenna
- NASA citizen science project: https://radiojove.gsfc.nasa.gov/

## Maser Detection with Small Dishes

### Eduard Mol — Mini Maser Telescope (EUCARA 2023)
- 1m dish + Inverto Ku PLL LNB on HEQ5 mount
- Detected W3(OH) and G188.94+0.89 at 12.178 GHz
- Integration times: 2–5+ hours
- Notes that 1m dish is "right at the limit" for methanol masers
- We have the PDF: `Eucara2023_Mini_Maser_Telescope_Eduard_Mol.pdf`

### Job Geheniau — Radio Astronomy JRT
- 1.5m dish + RTL-SDR, detected W3(OH) at hydroxyl 1665 MHz
- Also 12 GHz methanol: https://jgeheniau.wixsite.com/radio-astronomy/12-ghz-c3oh-methanol

### Reality Check for Our 60–80cm Dish
Our dish is smaller than Mol's 1m — maser detection will be harder.
W3(OH) is possible but may need **10+ hours integration** instead of 2–5.
Active SARA mailing list discussion: https://groups.google.com/g/sara-list/c/GL1xK_Kc-Q8

## Software

| Tool | Purpose | URL |
|------|---------|-----|
| **ezRA** | H-line data collection & analysis (Python3) | https://github.com/tedcline/ezRA |
| **Virgo** | GNU Radio spectrometer for radio astronomy | https://github.com/0xCoto/Virgo |
| **GNU Radio** | Signal processing framework | https://gnuradio.org |
| **SDR#** | General SDR receiver (Windows) | https://airspy.com |
| **Sky Pipe** | Strip chart recorder | https://radiosky.com |
| **RASDR** | Open-hardware SDR (LMS6002D, 300 MHz–3.8 GHz) | https://github.com/myriadrf/RASDR |

### ezRA — Most Relevant to Us
Complete Python3 toolchain for 1420 MHz hydrogen line:
- Data collection from RTL-SDR
- Spectral analysis and calibration
- Should integrate into our `sdr/hydrogen.py` pipeline

## SARA Observation Programs & Citizen Science

### Scientific Sections
- **Solar System**: Solar flare monitoring, Jupiter, meteor detection
- **Stellar**: Stellar radio source observations
- **Galactic & Cosmology**: Galactic center, Orion complex, Radio Galaxy Zoo
- **Electronics & Instrumentation**: Hardware development
- **Analytical**: Data analysis (contribute without a telescope)

### Citizen Science
- **Radio Galaxy Zoo** (Zooniverse): Cross-matching radio sources with host galaxies — https://www.zooniverse.org/projects/radio-galaxy-zoo
- **Radio JOVE**: Jupiter/solar data to NASA database
- **PSWS** (HamSCI): Ionospheric/geomagnetic monitoring — https://hamsci.org/psws-overview
- **SuperSID**: Solar flare data to Stanford Solar Center

## Community & Communication

- **Mailing list** (free, open): https://groups.google.com/g/sara-list
- **Monthly Zoom**: 1st Sunday, 2pm Eastern
- **Eastern Conference**: Annual, Green Bank Observatory, WV (August)
- **Western Conference**: Annual, varies (VLA/Socorro, NM)
- **Conference talks on YouTube**: Search "Society of Amateur Radio Astronomers"
- **RTL-SDR.com coverage**: https://www.rtl-sdr.com/tag/sara/

## European & Polish Connections

SARA is US-based with no formal European chapters. International membership works worldwide.

### Nearby Organizations
- **Astropeiler Stockert e.V.** (Germany): Wolfgang Herrmann presents at SARA regularly, operates 25m dish — https://www.astropeiler.de/
- **British Astronomical Association Radio Astronomy Group**: Dr. Andrew Thornett presents at SARA
- **Open Source Radio Telescopes** (Green Bank): https://opensourceradiotelescopes.org/

### Polish Organizations
- **PTMA** (Polish Amateur Astronomers' Society): https://ptma.pl/en/ — branches across Poland, thematic sections
- **PTA** (Polish Astronomical Society): https://www.pta.edu.pl/english — founded 1923, HQ in Warsaw
- **PZK** (Polish Amateur Radio Union): Amateur radio community
- **Torun Centre for Astronomy** (NCU): 32m radio telescope, methanol maser monitoring at 6.7 GHz — potential local contact for collaboration

## Key Resources to Bookmark

| Resource | URL |
|----------|-----|
| SARA main site | https://radio-astronomy.org/ |
| Mailing list | https://groups.google.com/g/sara-list |
| Getting started | https://radio-astronomy.org/getting-started |
| Beginner resources | https://radio-astronomy.org/node/296 |
| Store | https://radio-astronomy.org/store/ |
| Grants | https://radio-astronomy.org/grants |
| Publications | https://radio-astronomy.org/publications |
| Data logging formats | https://radio-astronomy.org/node/119 |
| Conference talks (RTL-SDR) | https://www.rtl-sdr.com/tag/sara/ |
| H-line guide (RTL-SDR) | https://www.rtl-sdr.com/cheap-and-easy-hydrogen-line-radio-astronomy-with-a-rtl-sdr-wifi-parabolic-grid-dish-lna-and-sdrsharp/ |

## Budget Telescope References

- **SARA 2022**: WiFi Grid + RTL-SDR telescopes, ~$179 — https://www.rtl-sdr.com/wifi-grid-rtl-sdr-radio-telescopes-featured-in-sara2022-conference-talks/
- **SARA Journal (2013)**: "Low Cost Hydrogen Line Radio Telescope for GBP 160 using the RTL SDR"
- **Wok-The-Hydrogen**: Wok-based H-line telescope — https://www.rtl-sdr.com/wok-the-hydrogen-a-low-cost-wok-based-hydrogen-line-radio-telescope/
- **2024 Western Conference**: Multiple talks on sub-$200 setups including military surplus antenna repurposing
