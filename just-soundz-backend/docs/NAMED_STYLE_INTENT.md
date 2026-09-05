# Named production-reference translation

Just Maker accepts natural prompts that mention a known artist or producer, but
the generation plan translates that reference into broad production controls.

Example:

`make a Kanye West type beat`

can become an original production plan emphasizing a soul-derived palette,
pitched/chopped cleared-source textures, gospel-influenced harmonic color,
punchy hip-hop drums, layered arrangement and polished mix treatment.

An industrial/electronic-era qualifier can instead favor sparse arrangement,
abrasive electronic texture, harder transients and minimal harmonic density.

The generation plan explicitly disables:

- artist voice cloning
- copying an existing melody
- copying an existing recording
- automatic use of uncleared copyrighted samples

This layer improves prompt usefulness while keeping the generated instrumental
original. Actual professional audio still requires a configured GPU generation
worker; this code translates and conditions the request but does not itself
supply model weights or GPU compute.
