import ctypes, wave, numpy as np, espeakng_loader as el, sys
lib=ctypes.cdll.LoadLibrary(el.get_library_path())
CB=ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
_buf=[]
@CB
def _cb(wav,n,ev):
    if n>0: _buf.append(np.ctypeslib.as_array(wav,shape=(n,)).copy())
    return 0
SR=lib.espeak_Initialize(2,0,el.get_data_path().encode(),0)  # AUDIO_OUTPUT_SYNCHRONOUS
lib.espeak_SetSynthCallback(_cb)
def synth(text, voice="az", rate=150, pitch=45):
    lib.espeak_SetVoiceByName(voice.encode())
    lib.espeak_SetParameter(1,rate,0); lib.espeak_SetParameter(3,pitch,0)
    _buf.clear(); b=text.encode()
    lib.espeak_Synth(b,len(b)+1,0,0,0,0x1,None,None)  # espeakCHARS_UTF8
    lib.espeak_Synchronize()
    return SR, (np.concatenate(_buf) if _buf else np.zeros(1,np.int16))
if __name__=="__main__":
    sr,a=synth(sys.argv[1]); w=wave.open(sys.argv[2],"wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(a.tobytes()); w.close(); print(sr,len(a)/sr)
