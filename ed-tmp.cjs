const fs=require('fs')
global.edit=function(p, pairs){
  let s=fs.readFileSync(p,'utf8').replace(/\r\n/g,'\n')
  for(const [a,b] of pairs){ if(!s.includes(a)) throw new Error(p+': '+a); s=s.replace(a,()=>b) }
  fs.writeFileSync(p,s.replace(/\n/g,'\r\n'))
}
