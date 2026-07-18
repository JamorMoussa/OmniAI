import sys 

sys.path.append("..")

from omniai.audio.speech import Kokoro
from omniai.core import Manifest


model = Kokoro.load(manifest=Manifest.load(
    path="/home/moussa/coding/omniai-dev/OmniAI/models/kokoro"
))


text = "I'm heading away from Dublin city centre, watching high rises, graffitied overpasses and traffic queues give way to pasturelands and swathes of red valerian swaying against the rails. Meadows of wild carrot and hawkbit break into wide expanses of boat-flecked open sea. It’s a Monday morning in June and I have the northbound Irish Rail almost entirely to myself. When most visitors think of Dublin, they picture Temple Bar's pubs, Georgian streets and literary legends. Yet Ireland's capital also sits on Dublin Bay, the world's only capital-city Unesco Biosphere Reserve, recognised for the way its wildlife and human inhabitants coexist in a working urban landscape. Most people don't even know there is a coast, says Helen Cole of Fáilte Ireland, the country's national tourism development authority. They weren't even aware that Dublin City, our capital city, is sitting on this amazing bay."

audio = model.create_stream(
    text=text,
    voice="af_heart"
)

for i, a in enumerate(audio):
    print(a)
    a.save(f"/home/moussa/coding/omniai-dev/OmniAI/outputs/audio_{i}.wav")

