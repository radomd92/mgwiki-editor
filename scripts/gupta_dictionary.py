"""Serial built-in read-only lookup batches; stop on failed batch."""
import subprocess

job='runs/gupta-empire-20261122'
english=['canonise','feudatory','maharajadhiraja','area','estimate','varna','gotra','Brahmin','yojana','maharaja','vassal','floruit','aristocracy','panegyrist','Vaishnavite','ashvamedha','veena','legend','era','chiefdom','shringara','corporal punishment','agnate','obverse','reverse','tirthankara','relief','profile','siege engine','heavy cavalry','horse archer','mahakavya','Brahmanism','endogamy','sangharama','vihara','dhyana','province','district','caste','urban','capital','mathematics','numeral','positional','base','sine','approximation','decimal','trigonometric function','square triangular number','formula','cosine','unit','Fibonacci number','axis','sphere','circumference','meridian','gnomon','corrosion','hydrate','hydrogen phosphate','cotton gin','roller','mahavihara','kavya','treatise','chaturanga','pawn','knight','rook','bishop','surgery','tetrastyle','prostyle','mukhalinga','pointed arch','coin','astronomy','metallurgy']
malagasy=['empira','mpanjaka','saranga','foko','soratra','fitsaboana','fandidiana','rafitra','fototra','sanda','lefa','raikipohy','toradroa','telozorirana','tandahatra','sfera','teza','refy','tombana','velarana','fiota','kristaly','landihazo','varingarina','andry','andohalambo','vola','fanisana','hetra','andriana','tononkalo','monasitera','eveka','tilikambo','astrônômia','fôsfôro']
def main():
    for edition,words in [('en',english),('mg',malagasy)]:
        for n in range(0,len(words),50):
            name=f'dictionary-{edition}-{n//50}'
            cmd=['python3','-m','mgwiki_editor','lookup-batch','--edition',edition,'--job',job,'--output-dir',f'{job}/{name}','--output',f'{job}/{name}-manifest.json','--summary']
            for word in words[n:n+50]:cmd+=['--word',word]
            subprocess.run(cmd,check=True)

if __name__ == '__main__':
    main()
