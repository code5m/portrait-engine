import {createIdentity} from './identity-model.mjs';
export const IDENTITIES = Object.freeze([
createIdentity({id:'lin-che',name:'林彻',age:35,faceDNA:{skull:{width:.42,height:.65},orbit:{depth:.74,width:.57},nose:{projection:.68,base:.41},jaw:{width:.68,angle:.78},cheek:{volume:.43}}}),
createIdentity({id:'zhou-qishan',name:'周启山',age:52,faceDNA:{skull:{width:.70,height:.43},brow:{depth:.77,height:.42},orbit:{depth:.65,width:.41},nose:{projection:.53,base:.63},jaw:{width:.83,angle:.71},cheek:{volume:.67}}}),
createIdentity({id:'third-portrait',name:'第三人物 / 研究',age:29,faceDNA:{skull:{width:.27,height:.55},orbit:{depth:.32,width:.67},nose:{projection:.36,base:.32},jaw:{width:.26,angle:.33},cheek:{volume:.72,height:.64},mouth:{width:.59}}})
]);
export function findIdentity(id) {return IDENTITIES.find(item=>item.id===id) ?? null;}
