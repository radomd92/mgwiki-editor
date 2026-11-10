"""Two small fidelity clarifications found during coordinator prose review."""
from pathlib import Path

JOB = Path('runs/earthquake-20261108')


if __name__ == '__main__':
    path = JOB/'draft.wiki'
    text = path.read_text(encoding='utf-8')
    text = text.replace("ary nihena hatramin' ny 730 000 ny mponina tao amin' ilay faritra",
                        "ary nihena olona hatramin' ny 730 000 ny isan' ny mponina tao amin' ilay faritra")
    text = text.replace("Ny haben' ireo bola araka ny endriny aseho amin' ny refy telo",
                        "Ny hadirin' ireo bola araka ny endriny aseho amin' ny refy telo")
    path.write_text(text, encoding='utf-8')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n## Precision review\n- Shaanxi: population decrease BY up to 730,000, not decline TO 730,000. Added Malagasy quantity wording only; numbers/causes unchanged.\n- Bubble-chart caption: volume (`hadiry`), not unspecified size. Source apparent 3D-volume meaning retained.\n')
