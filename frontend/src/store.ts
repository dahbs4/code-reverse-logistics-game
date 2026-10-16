import { create } from 'zustand'
import type { Game } from './types'
export async function api<T>(path:string,body?:unknown):Promise<T>{
 const r=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)})
 if(!r.ok){const x=await r.json();throw Error(typeof x.detail==='string'?x.detail:JSON.stringify(x.detail))}
 return r.json()
}
export const useGame=create<{game:Game|null;setGame:(g:Game)=>void}>((set)=>({game:null,setGame:(game)=>{localStorage.setItem('reverse-game',game.id);set({game})}}))
