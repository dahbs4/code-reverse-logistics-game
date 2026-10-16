import { describe,it,expect } from 'vitest'
import { num,compact,money,total } from './types'
describe('dashboard metrics',()=>{
 it('conserves inventory when composing all lifecycle states',()=>expect(total({upstream:2400,tender:2400,pickup:2400,transit:2400,yard:2400,receiving:100,staging:200})).toBe(12300))
 it('formats operational counts and finances',()=>{expect(num(1100000)).toBe('1,100,000');expect(compact(1100000)).toBe('1.1M');expect(money(-320)).toBe('-$320')})
})
