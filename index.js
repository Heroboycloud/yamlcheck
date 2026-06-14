var sh= require("shelljs")

sh.ls("*").forEach((f)=>{
console.log(f);
});
