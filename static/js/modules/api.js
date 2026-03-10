const API = {
    getFields: () => $.getJSON('/api/fields'),
    getFieldsData: () => $.getJSON('/api/fields_data'),
    getField: (id) => $.getJSON(`/api/field/${id}`),
    getOwners: () => $.getJSON('/api/owners'),
    
    addOwner: (name) => $.ajax({
        url: '/api/owner/add', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ name: name })
    }),
    
    deleteOwner: (id) => $.ajax({ url: `/api/owner/delete/${id}`, type: 'DELETE' }),
    
    addField: (geometry, name) => $.ajax({
        url: '/api/field/add', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ geometry: geometry, name: name })
    }),
    
    deleteField: (id) => $.ajax({ url: `/api/field/delete/${id}`, type: 'DELETE' }),
    
    updateField: (id, action, data) => $.ajax({
        url: `/api/field/${action}/${id}`, type: 'PUT', contentType: 'application/json',
        data: JSON.stringify(data)
    })
};
